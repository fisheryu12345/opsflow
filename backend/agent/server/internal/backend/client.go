package backend

import (
	"bytes"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"sync"
	"time"

	"opsflow/agent/server/internal/config"
)

// BatchResult represents a single command result to batch-write to Django.
type BatchResult struct {
	ExecID   string `json:"exec_id"`
	Status   string `json:"status"`
	Seq      int    `json:"seq,omitempty"`
	IsFinal  bool   `json:"is_final,omitempty"`
	Stdout   string `json:"stdout,omitempty"`
	Stderr   string `json:"stderr,omitempty"`
	ExitCode *int   `json:"exit_code,omitempty"`
	ErrorMsg string `json:"error_msg,omitempty"`
}

// Client handles async batch writing of command results to Django.
type Client struct {
	cfg       *config.DjangoConfig
	client    *http.Client
	buffer    []*BatchResult
	mu        sync.Mutex
	stopCh    chan struct{}
}

// NewClient creates a new Django backend client.
func NewClient(cfg *config.DjangoConfig) *Client {
	return &Client{
		cfg: cfg,
		client: &http.Client{
			Timeout: 10 * time.Second,
		},
		buffer: make([]*BatchResult, 0, cfg.BatchSize*2),
		stopCh: make(chan struct{}),
	}
}

// Start begins the periodic flush loop.
func (c *Client) Start() {
	go c.flushLoop()
	slog.Info("backend client started",
		"base_url", c.cfg.BaseURL,
		"batch_size", c.cfg.BatchSize,
		"batch_every", c.cfg.BatchEvery,
	)
}

// Stop gracefully stops the flush loop.
func (c *Client) Stop() {
	close(c.stopCh)
	c.flush() // flush remaining
}

// Push adds a result to the batch buffer.
func (c *Client) Push(result *BatchResult) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.buffer = append(c.buffer, result)
}

func (c *Client) flushLoop() {
	ticker := time.NewTicker(time.Duration(c.cfg.BatchEvery) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-c.stopCh:
			return
		case <-ticker.C:
			c.flush()
		}
	}
}

func (c *Client) flush() {
	c.mu.Lock()
	if len(c.buffer) == 0 {
		c.mu.Unlock()
		return
	}
	batch := c.buffer
	c.buffer = make([]*BatchResult, 0, c.cfg.BatchSize*2)
	c.mu.Unlock()

	if err := c.sendBatch(batch); err != nil {
		slog.Warn("batch write failed, will retry", "count", len(batch), "error", err)
		// Re-queue for retry
		c.mu.Lock()
		c.buffer = append(batch, c.buffer...)
		c.mu.Unlock()
	}
}

func (c *Client) sendBatch(results []*BatchResult) error {
	payload := map[string]any{"results": results}
	data, err := json.Marshal(payload)
	if err != nil {
		return fmt.Errorf("marshal batch: %w", err)
	}

	url := fmt.Sprintf("%s/api/agent/internal/batch_results/", c.cfg.BaseURL)
	req, err := http.NewRequest("POST", url, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if c.cfg.APIToken != "" {
		req.Header.Set("Authorization", fmt.Sprintf("Token %s", c.cfg.APIToken))
	}

	resp, err := c.client.Do(req)
	if err != nil {
		return fmt.Errorf("http post: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode >= 300 {
		return fmt.Errorf("http %d", resp.StatusCode)
	}
	return nil
}
