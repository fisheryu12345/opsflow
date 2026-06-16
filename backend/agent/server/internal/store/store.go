package store

import (
	"encoding/json"
	"fmt"
	"log/slog"
	"time"

	"go.etcd.io/bbolt"
)

// Store provides BoltDB-backed persistent storage for the Agent Server.
type Store struct {
	db *bbolt.DB
}

// NewStore opens or creates a BoltDB database.
func NewStore(path string) (*Store, error) {
	db, err := bbolt.Open(path, 0644, &bbolt.Options{Timeout: 1 * time.Second})
	if err != nil {
		return nil, fmt.Errorf("open boltdb: %w", err)
	}

	// Create buckets
	err = db.Update(func(tx *bbolt.Tx) error {
		buckets := []string{"agents", "tasks", "results", "upgrades"}
		for _, name := range buckets {
			if _, err := tx.CreateBucketIfNotExists([]byte(name)); err != nil {
				return fmt.Errorf("create bucket %s: %w", name, err)
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}

	slog.Info("boltdb store opened", "path", path)
	return &Store{db: db}, nil
}

// Close closes the database.
func (s *Store) Close() error {
	return s.db.Close()
}

// PutAgent stores agent metadata.
func (s *Store) PutAgent(agentID string, data any) error {
	return s.put("agents", agentID, data)
}

// GetAgent retrieves agent metadata.
func (s *Store) GetAgent(agentID string, dest any) error {
	return s.get("agents", agentID, dest)
}

// DeleteAgent removes agent metadata.
func (s *Store) DeleteAgent(agentID string) error {
	return s.db.Update(func(tx *bbolt.Tx) error {
		return tx.Bucket([]byte("agents")).Delete([]byte(agentID))
	})
}

// PutTask stores task state.
func (s *Store) PutTask(taskID string, data any) error {
	return s.put("tasks", taskID, data)
}

// GetAllTasks returns all task IDs.
func (s *Store) GetAllTasks() ([]string, error) {
	var ids []string
	err := s.db.View(func(tx *bbolt.Tx) error {
		b := tx.Bucket([]byte("tasks"))
		return b.ForEach(func(k, _ []byte) error {
			ids = append(ids, string(k))
			return nil
		})
	})
	return ids, err
}

func (s *Store) put(bucket, key string, data any) error {
	value, err := json.Marshal(data)
	if err != nil {
		return err
	}
	return s.db.Update(func(tx *bbolt.Tx) error {
		return tx.Bucket([]byte(bucket)).Put([]byte(key), value)
	})
}

func (s *Store) get(bucket, key string, dest any) error {
	return s.db.View(func(tx *bbolt.Tx) error {
		value := tx.Bucket([]byte(bucket)).Get([]byte(key))
		if value == nil {
			return fmt.Errorf("key not found: %s/%s", bucket, key)
		}
		return json.Unmarshal(value, dest)
	})
}
