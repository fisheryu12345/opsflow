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
)

// ChunkInfo describes a single chunk of a file transfer.
type ChunkInfo struct {
	Index    int    `json:"index"`
	Size     int64  `json:"size"`
	Checksum string `json:"checksum"`
}

// FileTask describes a file transfer task.
type FileTask struct {
	FileTaskID  string      `json:"file_task_id"`
	FileName    string      `json:"file_name"`
	FileSize    int64       `json:"file_size"`
	FileHash    string      `json:"file_hash"`
	ChunkSize   int         `json:"chunk_size"`
	ChunkCount  int         `json:"chunk_count"`
	TargetPath  string      `json:"target_path"`
	DownloadURL string      `json:"download_url"`
	Chunks      []ChunkInfo `json:"chunks"`
}

// Downloader handles downloading files from the Agent Server via HTTP.
type Downloader struct {
	workDir string
	client  *http.Client
}

// NewDownloader creates a new file downloader.
func NewDownloader(workDir string) *Downloader {
	return &Downloader{
		workDir: workDir,
		client:  &http.Client{},
	}
}

// DownloadFile downloads all chunks of a file and assembles them.
func (d *Downloader) DownloadFile(task *FileTask) error {
	slog.Info("starting file download", "file_task_id", task.FileTaskID,
		"file_name", task.FileName, "chunks", task.ChunkCount)

	// Create temp directory for chunks
	chunkDir := filepath.Join(d.workDir, "chunks", task.FileTaskID)
	if err := os.MkdirAll(chunkDir, 0755); err != nil {
		return fmt.Errorf("create chunk dir: %w", err)
	}
	defer os.RemoveAll(chunkDir)

	// Download all chunks concurrently with semaphore
	sem := make(chan struct{}, 4) // max 4 concurrent
	errCh := make(chan error, task.ChunkCount)

	for i := 0; i < task.ChunkCount; i++ {
		go func(idx int) {
			sem <- struct{}{}
			defer func() { <-sem }()

			chunkPath := filepath.Join(chunkDir, fmt.Sprintf("chunk-%05d", idx))
			chunkURL := fmt.Sprintf("%s/%s/%05d", task.DownloadURL, task.FileTaskID, idx)

			if err := d.downloadChunk(chunkURL, chunkPath); err != nil {
				errCh <- fmt.Errorf("chunk %d: %w", idx, err)
				return
			}
			slog.Debug("chunk downloaded", "index", idx, "file_task_id", task.FileTaskID)
			errCh <- nil
		}(i)
	}

	// Wait for all chunks
	var lastErr error
	for i := 0; i < task.ChunkCount; i++ {
		if err := <-errCh; err != nil {
			lastErr = err
		}
	}
	if lastErr != nil {
		return fmt.Errorf("download failed: %w", lastErr)
	}

	// Assemble chunks into final file
	if err := d.assembleFile(chunkDir, task); err != nil {
		return fmt.Errorf("assemble file: %w", err)
	}

	slog.Info("file download complete", "file_task_id", task.FileTaskID, "path", task.TargetPath)
	return nil
}

func (d *Downloader) downloadChunk(url, path string) error {
	resp, err := d.client.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("HTTP %d", resp.StatusCode)
	}

	out, err := os.Create(path)
	if err != nil {
		return err
	}
	defer out.Close()

	_, err = io.Copy(out, resp.Body)
	return err
}

func (d *Downloader) assembleFile(chunkDir string, task *FileTask) error {
	// Ensure target directory exists
	targetDir := filepath.Dir(task.TargetPath)
	if err := os.MkdirAll(targetDir, 0755); err != nil {
		return err
	}

	out, err := os.Create(task.TargetPath)
	if err != nil {
		return err
	}
	defer out.Close()

	hasher := sha256.New()
	multiWriter := io.MultiWriter(out, hasher)

	for i := 0; i < task.ChunkCount; i++ {
		chunkPath := filepath.Join(chunkDir, fmt.Sprintf("chunk-%05d", i))
		f, err := os.Open(chunkPath)
		if err != nil {
			return fmt.Errorf("open chunk %d: %w", i, err)
		}
		_, err = io.Copy(multiWriter, f)
		f.Close()
		if err != nil {
			return fmt.Errorf("copy chunk %d: %w", i, err)
		}
	}

	// Verify complete file hash
	actualHash := hex.EncodeToString(hasher.Sum(nil))
	if task.FileHash != "" && actualHash != task.FileHash {
		os.Remove(task.TargetPath)
		return fmt.Errorf("checksum mismatch: expected %s, got %s", task.FileHash, actualHash)
	}

	return nil
}

// Uploader handles uploading files to the Agent Server.
type Uploader struct {
	serverURL string
	client    *http.Client
}

// NewUploader creates a new file uploader.
func NewUploader(serverURL string) *Uploader {
	return &Uploader{
		serverURL: serverURL,
		client:    &http.Client{},
	}
}

// UploadFile uploads a file by splitting it into chunks.
func (u *Uploader) UploadFile(localPath string, chunkSize int) (*FileTask, error) {
	file, err := os.Open(localPath)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	stat, err := file.Stat()
	if err != nil {
		return nil, err
	}

	fileSize := stat.Size()
	chunkCount := int((fileSize + int64(chunkSize) - 1) / int64(chunkSize))

	// Calculate file hash
	hasher := sha256.New()
	if _, err := io.Copy(hasher, file); err != nil {
		return nil, err
	}
	fileHash := hex.EncodeToString(hasher.Sum(nil))
	file.Seek(0, 0)

	task := &FileTask{
		FileName:   filepath.Base(localPath),
		FileSize:   fileSize,
		FileHash:   fileHash,
		ChunkSize:  chunkSize,
		ChunkCount: chunkCount,
	}

	return task, nil
}
