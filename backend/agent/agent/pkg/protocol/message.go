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
