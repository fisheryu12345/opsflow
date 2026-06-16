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
	"strconv"
	"strings"
	"sync"
)

// ChunkStore manages file chunk storage on the Agent Server.
type ChunkStore struct {
	dataDir string
	mu      sync.RWMutex
}

// NewChunkStore creates a new chunk store.
func NewChunkStore(dataDir string) *ChunkStore {
	chunkDir := filepath.Join(dataDir, "chunks")
	if err := os.MkdirAll(chunkDir, 0755); err != nil {
		slog.Warn("failed to create chunk dir", "path", chunkDir, "error", err)
	}
	return &ChunkStore{dataDir: chunkDir}
}

// ChunkHandler returns an HTTP handler for chunk download/upload.
func (cs *ChunkStore) ChunkHandler() http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		// URL pattern: /chunks/<file_task_id>/<chunk_index>
		parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/chunks/"), "/")
		if len(parts) != 2 {
			http.Error(w, "invalid path", http.StatusBadRequest)
			return
		}
		taskID, chunkIdx := parts[0], parts[1]

		switch r.Method {
		case http.MethodGet:
			cs.serveChunk(w, r, taskID, chunkIdx)
		case http.MethodPut:
			cs.storeChunk(w, r, taskID, chunkIdx)
		default:
			http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		}
	}
}

func (cs *ChunkStore) serveChunk(w http.ResponseWriter, r *http.Request, taskID, chunkIdx string) {
	chunkPath := filepath.Join(cs.dataDir, taskID, fmt.Sprintf("chunk-%05s", chunkIdx))
	w.Header().Set("Content-Type", "application/octet-stream")
	http.ServeFile(w, r, chunkPath)
}

func (cs *ChunkStore) storeChunk(w http.ResponseWriter, r *http.Request, taskID, chunkIdx string) {
	taskDir := filepath.Join(cs.dataDir, taskID)
	if err := os.MkdirAll(taskDir, 0755); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	chunkPath := filepath.Join(taskDir, fmt.Sprintf("chunk-%05s", chunkIdx))
	out, err := os.Create(chunkPath)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	defer out.Close()

	written, err := io.Copy(out, r.Body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.WriteHeader(http.StatusOK)
	fmt.Fprintf(w, `{"written":%d}`, written)
}

// Cleanup removes stale chunk directories.
func (cs *ChunkStore) Cleanup() {
	entries, err := os.ReadDir(cs.dataDir)
	if err != nil {
		return
	}
	for _, entry := range entries {
		if entry.IsDir() {
			// Check access time to determine staleness
			// (In production, track task completion time)
			path := filepath.Join(cs.dataDir, entry.Name())
			os.RemoveAll(path)
			slog.Debug("cleaned up chunk dir", "path", path)
		}
	}
}

// SplitFile splits a file into chunks and stores them.
func (cs *ChunkStore) SplitFile(taskID, sourcePath string, chunkSize int) (int, string, error) {
	file, err := os.Open(sourcePath)
	if err != nil {
		return 0, "", err
	}
	defer file.Close()

	// Calculate file hash
	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return 0, "", err
	}
	fileHash := hex.EncodeToString(hasher.Sum(nil))
	file.Seek(0, 0)

	taskDir := filepath.Join(cs.dataDir, taskID)
	os.MkdirAll(taskDir, 0755)

	buf := make([]byte, chunkSize)
	chunkCount := 0

	for {
		n, err := file.Read(buf)
		if n > 0 {
			chunkPath := filepath.Join(taskDir, fmt.Sprintf("chunk-%05d", chunkCount))
			if werr := os.WriteFile(chunkPath, buf[:n], 0644); werr != nil {
				return 0, "", werr
			}
			chunkCount++
		}
		if err == io.EOF {
			break
		}
		if err != nil {
			return 0, "", err
		}
	}

	return chunkCount, fileHash, nil
}

// AssembleFile assembles chunks back into the original file.
func (cs *ChunkStore) AssembleFile(taskID, targetPath string, chunkCount int) error {
	out, err := os.Create(targetPath)
	if err != nil {
		return err
	}
	defer out.Close()

	for i := 0; i < chunkCount; i++ {
		chunkPath := filepath.Join(cs.dataDir, taskID, fmt.Sprintf("chunk-%05d", i))
		f, err := os.Open(chunkPath)
		if err != nil {
			return fmt.Errorf("chunk %d: %w", i, err)
		}
		_, err = io.Copy(out, f)
		f.Close()
		if err != nil {
			return err
		}
	}
	return nil
}

// ParseChunkRequest parses a chunk upload/download URL.
func ParseChunkRange(rangeHeader string) (start, end int64, err error) {
	if rangeHeader == "" {
		return 0, 0, nil
	}
	r := strings.TrimPrefix(rangeHeader, "bytes=")
	parts := strings.Split(r, "-")
	if len(parts) != 2 {
		return 0, 0, fmt.Errorf("invalid range: %s", rangeHeader)
	}
	start, _ = strconv.ParseInt(parts[0], 10, 64)
	end, _ = strconv.ParseInt(parts[1], 10, 64)
	return start, end, nil
}
