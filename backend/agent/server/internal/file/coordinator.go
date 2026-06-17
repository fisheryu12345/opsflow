package file

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"time"

	"opsflow/agent/server/internal/ws"
)

// Coordinator handles file transfer coordination: pull → chunk → store → notify Agent.
type Coordinator struct {
	store      *ChunkStore
	wsServer   *ws.Server
	client     *http.Client
	serverAddr string // address for agents to download chunks (e.g. "192.168.1.36:18080")
}

// NewCoordinator creates a file transfer coordinator.
func NewCoordinator(dataDir string, wsServer *ws.Server, serverAddr string) *Coordinator {
	return &Coordinator{
		store:      NewChunkStore(dataDir),
		wsServer:   wsServer,
		client:     &http.Client{Timeout: 30 * time.Minute},
		serverAddr: serverAddr,
	}
}

// PushTask describes an incoming file push request from Django.
type PushTask struct {
	FileTaskID  string `json:"file_task_id"`
	TargetHost  string `json:"target_host"`
	TargetPath  string `json:"target_path"`
	SourcePath  string `json:"source_path"`
	FileName    string `json:"file_name"`
	FileSize    int64  `json:"file_size"`
	FileHash    string `json:"file_hash"`
	DownloadURL string `json:"download_url"`
	ServerAddr  string `json:"server_addr"` // added by API handler
}

// ChunkHandler returns the HTTP handler for chunk download.
func (c *Coordinator) ChunkHandler() http.HandlerFunc {
	return c.store.ChunkHandler()
}

// HandlePush is called when Django sends a file push request.
func (c *Coordinator) HandlePush(task *PushTask) error {
	slog.Info("file push coordinator started", "task_id", task.FileTaskID, "file", task.FileName)

	// Step 1: Download original file from Django
	tmpFile := filepath.Join(c.store.dataDir, "uploads", task.FileTaskID+".tmp")
	if err := os.MkdirAll(filepath.Dir(tmpFile), 0755); err != nil {
		return fmt.Errorf("create upload dir: %w", err)
	}

	if err := c.downloadOriginal(task.DownloadURL, tmpFile); err != nil {
		return fmt.Errorf("download original: %w", err)
	}
	defer os.Remove(tmpFile)

	// Step 2: Calculate file hash
	actualHash, fileSize, err := c.fileHash(tmpFile)
	if err != nil {
		return fmt.Errorf("hash: %w", err)
	}
	if task.FileHash != "" && actualHash != task.FileHash {
		return fmt.Errorf("hash mismatch: expected=%s actual=%s", task.FileHash, actualHash)
	}
	task.FileHash = actualHash
	task.FileSize = fileSize

	// Step 3: Split into chunks (4MB each)
	chunkSize := 4 * 1024 * 1024
	chunkCount, _, err := c.store.SplitFile(task.FileTaskID, tmpFile, chunkSize)
	if err != nil {
		return fmt.Errorf("split file: %w", err)
	}
	slog.Info("file split into chunks", "task_id", task.FileTaskID, "chunks", chunkCount)

	// Step 4: Notify agent via WS
	c.notifyAgent(task, chunkCount, chunkSize)

	return nil
}

func (c *Coordinator) downloadOriginal(url, dest string) error {
	slog.Info("downloading original file", "url", url)
	resp, err := c.client.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	out, err := os.Create(dest)
	if err != nil {
		return err
	}
	defer out.Close()

	written, err := io.Copy(out, resp.Body)
	if err != nil {
		return err
	}
	slog.Info("original file downloaded", "size", written)
	return nil
}

func (c *Coordinator) fileHash(path string) (string, int64, error) {
	f, err := os.Open(path)
	if err != nil {
		return "", 0, err
	}
	defer f.Close()

	hasher := sha256.New()
	written, err := io.Copy(hasher, f)
	if err != nil {
		return "", 0, err
	}
	return hex.EncodeToString(hasher.Sum(nil)), written, nil
}

func (c *Coordinator) notifyAgent(task *PushTask, chunkCount, chunkSize int) {
	// Find agent by target host
	var agent *ws.AgentConn
	if task.TargetHost != "" {
		agent = c.wsServer.GetAgentByHost(task.TargetHost)
	}
	if agent == nil {
		// Fallback: broadcast to all (bad for prod, OK for dev)
		slog.Warn("no agent found for host, broadcasting", "host", task.TargetHost)
		c.wsServer.Broadcast(map[string]any{
			"version": "1.0",
			"type":    "file_push",
			"body": map[string]any{
				"file_task_id": task.FileTaskID,
				"file_name":    task.FileName,
				"file_size":    task.FileSize,
				"file_hash":    task.FileHash,
				"chunk_size":   chunkSize,
				"chunk_count":  chunkCount,
				"target_path":  task.TargetPath,
				"download_url": fmt.Sprintf("http://%s/chunks/%s", c.serverAddr, task.FileTaskID),
			},
		})
		return
	}

	msg := map[string]any{
		"version": "1.0",
		"type":    "file_push",
		"target":  map[string]any{"agent_id": agent.AgentID},
		"body": map[string]any{
			"file_task_id": task.FileTaskID,
			"file_name":    task.FileName,
			"file_size":    task.FileSize,
			"file_hash":    task.FileHash,
			"chunk_size":   chunkSize,
			"chunk_count":  chunkCount,
			"target_path":  task.TargetPath,
			"download_url": fmt.Sprintf("http://%s/chunks/%s", c.serverAddr, task.FileTaskID),
		},
	}
	if err := agent.SendJSON(msg); err != nil {
		slog.Error("send file_push to agent failed", "agent_id", agent.AgentID, "error", err)
	} else {
		slog.Info("file_push sent to agent", "agent_id", agent.AgentID, "task_id", task.FileTaskID)
	}
}
