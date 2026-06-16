package core

import (
	"bytes"
	"context"
	"fmt"
	"log/slog"
	"os"
	"os/exec"
	"strings"
	"time"

	"opsflow/agent/agent/pkg/protocol"
)

// Executor handles local command execution with streaming output.
type Executor struct {
	wsClient *WSClient
}

// NewExecutor creates a new Executor.
func NewExecutor(wsClient *WSClient) *Executor {
	return &Executor{wsClient: wsClient}
}

// Execute runs a command and streams the result back to the server.
func (e *Executor) Execute(cmd *protocol.CommandBody) {
	slog.Info("executing command", "exec_id", cmd.ExecID, "script_type", cmd.ScriptType)

	startTime := time.Now()
	ctx := context.Background()

	if cmd.Timeout > 0 {
		var cancel context.CancelFunc
		ctx, cancel = context.WithTimeout(ctx, time.Duration(cmd.Timeout)*time.Second)
		defer cancel()
	}

	// Determine the shell command
	shell, shellArg := e.resolveShell(cmd.ScriptType)

	var c *exec.Cmd
	if cmd.ScriptContent != "" {
		c = exec.CommandContext(ctx, shell, shellArg, cmd.ScriptContent)
	} else {
		c = exec.CommandContext(ctx, shell, shellArg)
	}

	// Set working directory
	if cmd.WorkDir != "" {
		c.Dir = cmd.WorkDir
	}

	// Set environment variables
	if len(cmd.EnvVars) > 0 {
		c.Env = os.Environ()
		for k, v := range cmd.EnvVars {
			c.Env = append(c.Env, fmt.Sprintf("%s=%s", k, v))
		}
	}

	// Capture stdout and stderr
	var stdoutBuf, stderrBuf bytes.Buffer
	c.Stdout = &stdoutBuf
	c.Stderr = &stderrBuf

	// Execute
	err := c.Run()

	// Collect results
	duration := time.Since(startTime)
	exitCode := 0
	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = -1
		}
	}

	stdout := stdoutBuf.String()
	stderr := stderrBuf.String()

	// Truncate output if limit is set
	outputLimit := cmd.OutputLimit
	if outputLimit == 0 {
		outputLimit = 10 * 1024 * 1024 // default 10MB
	}
	if int64(len(stdout)) > outputLimit {
		stdout = stdout[:outputLimit] + "\n... [truncated]"
	}

	seq := 1
	isFinal := true
	exitCodeCopy := exitCode

	// Send final result
	result := &protocol.CommandResultBody{
		ExecID:     cmd.ExecID,
		Seq:        seq,
		IsFinal:    isFinal,
		Stdout:     stdout,
		Stderr:     stderr,
		ExitCode:   &exitCodeCopy,
		FinishTime: time.Now().Unix(),
	}
	if err != nil {
		result.Error = err.Error()
	}

	msg := protocol.NewCommandResult("agent", result)
	if e.wsClient != nil {
		e.wsClient.SendJSON(msg)
	}

	// Also write result to local log
	slog.Info("command completed",
		"exec_id", cmd.ExecID,
		"exit_code", exitCode,
		"duration", duration,
		"stdout_size", len(stdout),
		"stderr_size", len(stderr),
	)
}

// resolveShell returns the appropriate shell for the script type.
func (e *Executor) resolveShell(scriptType string) (string, string) {
	switch strings.ToLower(scriptType) {
	case "bat":
		return "cmd.exe", "/c"
	case "powershell":
		return "powershell.exe", "-Command"
	case "python":
		return "python", "-c"
	default: // shell
		return "/bin/sh", "-c"
	}
}
