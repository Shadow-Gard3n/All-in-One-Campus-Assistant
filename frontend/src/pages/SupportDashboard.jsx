
import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";

function SupportDashboard() {
    const { user, logout } = useAuth();

    const [conversations, setConversations] = useState([]);
    const [selectedConversation, setSelectedConversation] = useState(null);
    const [message, setMessage] = useState("");

    const [loading, setLoading] = useState(true);
    const [conversationLoading, setConversationLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState("");

    // --------------------------------------------------
    // LOAD CONVERSATIONS
    // --------------------------------------------------

    const loadConversations = async () => {
        try {
            setLoading(true);
            setError("");

            const response = await api.get(
                "/support/conversations"
            );

            setConversations(response.data);

        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to load conversations"
            );
        } finally {
            setLoading(false);
        }
    };

    // --------------------------------------------------
    // LOAD SINGLE CONVERSATION
    // --------------------------------------------------

    const openConversation = async (conversationId) => {
        try {
            setConversationLoading(true);
            setError("");

            const response = await api.get(
                `/support/conversations/${conversationId}`
            );

            setSelectedConversation(response.data);

        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to load conversation"
            );
        } finally {
            setConversationLoading(false);
        }
    };

    // --------------------------------------------------
    // TAKE CONVERSATION
    // --------------------------------------------------

    const takeConversation = async () => {
        if (!selectedConversation) {
            return;
        }

        try {
            await api.post(
                `/support/conversations/${selectedConversation.id}/take`
            );

            await openConversation(
                selectedConversation.id
            );

            await loadConversations();

        } catch (error) {
            alert(
                error.response?.data?.detail ||
                "Failed to take conversation"
            );
        }
    };

    // --------------------------------------------------
    // SEND MESSAGE
    // --------------------------------------------------

    const sendMessage = async (e) => {
        e.preventDefault();

        if (!message.trim()) {
            return;
        }

        if (!selectedConversation) {
            return;
        }

        try {
            setSending(true);

            const response = await api.post(
                `/support/conversations/${selectedConversation.id}/messages`,
                {
                    message: message.trim()
                }
            );

            setMessage("");

            // Backend returns the final AI response.
            await openConversation(
                selectedConversation.id
            );

            await loadConversations();

        } catch (error) {
            console.error(error);

            alert(
                error.response?.data?.detail ||
                "Failed to send message"
            );
        } finally {
            setSending(false);
        }
    };

    // --------------------------------------------------
    // RESOLVE CONVERSATION
    // --------------------------------------------------

    const resolveConversation = async () => {
        if (!selectedConversation) {
            return;
        }

        try {
            await api.post(
                `/support/conversations/${selectedConversation.id}/resolve`
            );

            setSelectedConversation(null);

            await loadConversations();

        } catch (error) {
            alert(
                error.response?.data?.detail ||
                "Failed to resolve conversation"
            );
        }
    };

    // --------------------------------------------------
    // INITIAL LOAD
    // --------------------------------------------------

    useEffect(() => {
        loadConversations();
    }, []);

    // --------------------------------------------------
    // LOADING
    // --------------------------------------------------

    if (loading) {
        return (
            <div className="support-page">
                <div className="support-loading">
                    Loading support dashboard...
                </div>
            </div>
        );
    }

    return (
        <div className="support-page">

            {/* ========================================= */}
            {/* HEADER */}
            {/* ========================================= */}

            <header className="support-header">

                <div>
                    <h1>OneDesk AI</h1>

                    <p>
                        Support Agent Dashboard
                    </p>
                </div>

                <div className="support-header-user">

                    <div>
                        <strong>
                            {user?.name}
                        </strong>

                        <span>
                            Support Agent
                        </span>
                    </div>

                    <button
                        className="logout-button"
                        onClick={logout}
                    >
                        Logout
                    </button>

                </div>

            </header>


            {/* ========================================= */}
            {/* MAIN */}
            {/* ========================================= */}

            <main className="support-content">

                {error && (
                    <div className="support-error">
                        {error}
                    </div>
                )}


                <div className="support-layout">

                    {/* ================================= */}
                    {/* LEFT: CONVERSATIONS */}
                    {/* ================================= */}

                    <aside className="conversation-sidebar">

                        <div className="conversation-sidebar-header">

                            <div>
                                <h2>Conversations</h2>

                                <p>
                                    {conversations.length} waiting
                                </p>
                            </div>

                            <button
                                className="refresh-button"
                                onClick={loadConversations}
                            >
                                ↻
                            </button>

                        </div>


                        {conversations.length === 0 ? (

                            <div className="conversation-empty">
                                <div className="empty-icon">
                                    ✓
                                </div>

                                <h3>
                                    All caught up
                                </h3>

                                <p>
                                    There are no conversations
                                    waiting for support.
                                </p>
                            </div>

                        ) : (

                            <div className="conversation-list">

                                {conversations.map(
                                    (conversation) => (

                                        <button
                                            key={conversation.id}
                                            className={
                                                "conversation-item " +
                                                (
                                                    selectedConversation?.id ===
                                                    conversation.id
                                                        ? "selected"
                                                        : ""
                                                )
                                            }
                                            onClick={() =>
                                                openConversation(
                                                    conversation.id
                                                )
                                            }
                                        >

                                            <div className="conversation-item-top">

                                                <strong>
                                                    {
                                                        conversation.user?.name ||
                                                        "Unknown User"
                                                    }
                                                </strong>

                                                <span>
                                                    {
                                                        conversation.status ===
                                                        "waiting_for_agent"
                                                            ? "Waiting"
                                                            : "Active"
                                                    }
                                                </span>

                                            </div>

                                            <p>
                                                {
                                                    conversation.title ||
                                                    "No message"
                                                }
                                            </p>

                                        </button>

                                    )
                                )}

                            </div>
                        )}

                    </aside>


                    {/* ================================= */}
                    {/* RIGHT: CONVERSATION */}
                    {/* ================================= */}

                    <section className="conversation-panel">

                        {!selectedConversation ? (

                            <div className="conversation-placeholder">

                                <div className="placeholder-icon">
                                    💬
                                </div>

                                <h2>
                                    Select a conversation
                                </h2>

                                <p>
                                    Choose a conversation from
                                    the left to view the user's
                                    question.
                                </p>

                            </div>

                        ) : conversationLoading ? (

                            <div className="conversation-placeholder">
                                Loading conversation...
                            </div>

                        ) : (

                            <>

                                {/* ------------------------- */}
                                {/* CONVERSATION HEADER */}
                                {/* ------------------------- */}

                                <div className="conversation-header">

                                    <div>

                                        <h2>
                                            {
                                                selectedConversation
                                                    .user?.name ||
                                                "Unknown User"
                                            }
                                        </h2>

                                        <p>
                                            {
                                                selectedConversation
                                                    .user?.email
                                            }
                                        </p>

                                    </div>

                                    <div className="conversation-header-actions">

                                        <span className={
                                            "status-badge " +
                                            selectedConversation.status
                                        }>
                                            {
                                                selectedConversation.status
                                            }
                                        </span>

                                        {!selectedConversation.assigned_agent_id && (
                                            <button
                                                className="take-button"
                                                onClick={
                                                    takeConversation
                                                }
                                            >
                                                Take Conversation
                                            </button>
                                        )}

                                    </div>

                                </div>


                                {/* ------------------------- */}
                                {/* MESSAGES */}
                                {/* ------------------------- */}

                                <div className="messages-container">

                                    {selectedConversation.messages
                                        ?.map(
                                            (msg, index) => (

                                                <div
                                                    key={index}
                                                    className={
                                                        `message-row ${msg.sender}`
                                                    }
                                                >

                                                    <div className="message-bubble">

                                                        <div className="message-sender">
                                                            {
                                                                msg.sender ===
                                                                "user"
                                                                    ? "User"
                                                                    : msg.sender ===
                                                                      "ai"
                                                                    ? "AI"
                                                                    : "Support Agent"
                                                            }
                                                        </div>

                                                        <div className="message-text">
                                                            {msg.message}
                                                        </div>

                                                    </div>

                                                </div>

                                            )
                                        )}

                                </div>


                                {/* ------------------------- */}
                                {/* REPLY AREA */}
                                {/* ------------------------- */}

                                {selectedConversation.status ===
                                    "waiting_for_agent" && (
                                    <form
                                        className="support-reply"
                                        onSubmit={sendMessage}
                                    >

                                        <textarea
                                            value={message}
                                            onChange={(e) =>
                                                setMessage(
                                                    e.target.value
                                                )
                                            }
                                            placeholder="Write your answer..."
                                            rows={4}
                                            disabled={sending}
                                        />

                                        <div className="reply-footer">

                                            <span>
                                                Your answer will be
                                                processed by AI before
                                                being shown to the user.
                                            </span>

                                            <button
                                                type="submit"
                                                className="send-button"
                                                disabled={
                                                    sending ||
                                                    !message.trim() ||
                                                    !selectedConversation.assigned_agent_id
                                                }
                                            >
                                                {sending
                                                    ? "Sending..."
                                                    : "Send Answer"}
                                            </button>

                                        </div>

                                    </form>
                                )}


                                {/* ------------------------- */}
                                {/* RESOLVE */}
                                {/* ------------------------- */}

                                {selectedConversation.assigned_agent_id &&
                                    selectedConversation.status !==
                                        "resolved" && (

                                    <div className="resolve-area">

                                        <button
                                            className="resolve-button"
                                            onClick={
                                                resolveConversation
                                            }
                                        >
                                            Mark as Resolved
                                        </button>

                                    </div>
                                )}

                            </>
                        )}

                    </section>

                </div>

            </main>

        </div>
    );
}

export default SupportDashboard;
