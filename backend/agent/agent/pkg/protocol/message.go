package protocol

import (
	"crypto/rand"
	"fmt"
	"time"
)

// NewMsgID generates a unique message ID using crypto/rand.
func NewMsgID() string {
	b := make([]byte, 16)
	rand.Read(b)
	return fmt.Sprintf("%x-%x-%x-%x-%x", b[0:4], b[4:6], b[6:8], b[8:10], b[10:])
}

// NewMessage creates a new message with the given type and body.
func NewMessage(msgType MessageType, source string, body any) *Message {
	return &Message{
		Version:   "1.0",
		MsgID:     NewMsgID(),
		Type:      msgType,
		Topic:     "agent:*",
		Timestamp: time.Now().UTC().Format(time.RFC3339),
		Source:    source,
		Body:      body,
		TTL:       300,
	}
}

// NewCommand creates a command message.
func NewCommand(source string, body *CommandBody) *Message {
	return NewMessage(MsgCommand, source, body)
}

// NewCommandResult creates a streaming command result message.
func NewCommandResult(source string, body *CommandResultBody) *Message {
	return NewMessage(MsgCommandResult, source, body)
}

// NewHeartbeat creates a heartbeat message.
func NewHeartbeat(source string, body *HeartbeatBody) *Message {
	return NewMessage(MsgHeartbeat, source, body)
}

// NewRegister creates a register message.
func NewRegister(source string, body *RegisterBody) *Message {
	return NewMessage(MsgRegister, source, body)
}

// NewRegisterAck creates a register acknowledgment.
func NewRegisterAck(source string, body *RegisterAckBody) *Message {
	return NewMessage(MsgRegisterAck, source, body)
}

// NewSetConfig creates a config update message.
func NewSetConfig(source string, body *SetConfigBody) *Message {
	return NewMessage(MsgSetConfig, source, body)
}

// NewProcessControl creates a process control message.
func NewProcessControl(source string, body *ProcessControlBody) *Message {
	return NewMessage(MsgProcessControl, source, body)
}

// NewProcessCtrlResult creates a process control result message.
func NewProcessCtrlResult(source string, body *ProcessCtrlResultBody) *Message {
	return NewMessage(MsgProcessCtrlResult, source, body)
}

// NewAppRegister creates an app register message.
func NewAppRegister(source string, body *AppRegisterBody) *Message {
	return NewMessage(MsgAppRegister, source, body)
}

// NewAppUnregister creates an app unregister message.
func NewAppUnregister(source string, body *AppUnregisterBody) *Message {
	return NewMessage(MsgAppUnregister, source, body)
}

// NewAppList creates an app list request.
func NewAppList(source string) *Message {
	return NewMessage(MsgAppList, source, nil)
}

// NewAppListResult creates an app list response.
func NewAppListResult(source string, body *AppListBody) *Message {
	return NewMessage(MsgAppListResult, source, body)
}
