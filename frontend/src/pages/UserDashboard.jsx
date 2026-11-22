// import { useState } from "react";

// import { useAuth } from "../context/AuthContext";

// import api from "../services/api";


// function UserDashboard() {

//     const { user, logout } = useAuth();

//     const [message, setMessage] = useState("");

//     const [messages, setMessages] = useState([]);

//     const [conversationId, setConversationId] = useState(null);

//     const [sending, setSending] = useState(false);

//     const [error, setError] = useState("");


//     // =========================================================
//     // NEW CHAT
//     // =========================================================
//     // IMPORTANT:
//     // This DOES NOT create a conversation in MongoDB.
//     //
//     // It only resets the frontend state.
//     //
//     // MongoDB conversation is created only when the
//     // user actually sends the first message.
//     // =========================================================

//     const startConversation = () => {

//         setConversationId(null);

//         setMessages([]);

//         setMessage("");

//         setError("");
//     };


//     // =========================================================
//     // SEND MESSAGE
//     // =========================================================

//     const sendMessage = async (e) => {

//         e.preventDefault();

//         if (!message.trim() || sending) {
//             return;
//         }


//         try {

//             setSending(true);

//             setError("");


//             const userMessage = message.trim();


//             // ---------------------------------------------
//             // Show user message immediately
//             // ---------------------------------------------

//             setMessages((prev) => [

//                 ...prev,

//                 {
//                     sender: "user",
//                     message: userMessage
//                 }

//             ]);


//             setMessage("");


//             // ---------------------------------------------
//             // Get existing conversation ID
//             // ---------------------------------------------

//             let id = conversationId;


//             // ---------------------------------------------
//             // IMPORTANT:
//             //
//             // If this is the first message of a new chat,
//             // THEN create the conversation.
//             //
//             // This prevents empty conversations.
//             // ---------------------------------------------

//             if (!id) {

//                 const conversationResponse =
//                     await api.post("/conversations");


//                 id = conversationResponse.data.id;


//                 setConversationId(id);
//             }


//             // ---------------------------------------------
//             // Send the actual message
//             // ---------------------------------------------

//             const response = await api.post(

//                 `/conversations/${id}/messages`,

//                 {
//                     message: userMessage
//                 }

//             );


//             // ---------------------------------------------
//             // Show AI response
//             // ---------------------------------------------

//             setMessages((prev) => [

//                 ...prev,

//                 {
//                     sender: "ai",
//                     message: response.data.message
//                 }

//             ]);

//         }


//         catch (error) {

//             console.error(
//                 "Send message error:",
//                 error
//             );


//             setError(

//                 error.response?.data?.detail ||

//                 "Failed to send message"

//             );

//         }


//         finally {

//             setSending(false);

//         }

//     };


//     // =========================================================
//     // RENDER
//     // =========================================================

//     return (

//         <div className="user-dashboard">


//             {/* =================================================
//                 HEADER
//             ================================================= */}

//             <header className="dashboard-header">


//                 <div>

//                     <h1>
//                         OneDesk AI
//                     </h1>


//                     <p>
//                         Hello, {user?.name || "User"}
//                     </p>

//                 </div>


//                 <button
//                     onClick={logout}
//                     className="logout-button"
//                 >

//                     Logout

//                 </button>


//             </header>



//             {/* =================================================
//                 MAIN CHAT
//             ================================================= */}

//             <main className="chat-container">


//                 {/* =================================================
//                     NO ACTIVE CONVERSATION

//                     IMPORTANT:

//                     No API request happens here.

//                     User can type directly.

//                     Conversation is created only after Send.
//                 ================================================= */}

//                 {!conversationId ? (

//                     <div className="chat-welcome">


//                         {/* Welcome icon */}

//                         <div className="welcome-icon">
//                             ✨
//                         </div>


//                         <h2>
//                             How can I help you?
//                         </h2>


//                         <p>
//                             Ask OneDesk AI about IT, HR,
//                             Finance, or any other department
//                             in your organisation.
//                         </p>


//                         {/* Error */}

//                         {error && (

//                             <div className="error-message">

//                                 {error}

//                             </div>

//                         )}


//                         {/* =================================================
//                             WELCOME INPUT
//                         ================================================= */}

//                         <form
//                             className="welcome-input-area"
//                             onSubmit={sendMessage}
//                         >


//                             <input

//                                 type="text"

//                                 className="welcome-input"

//                                 placeholder="Ask OneDesk AI anything..."

//                                 value={message}

//                                 onChange={(e) =>
//                                     setMessage(
//                                         e.target.value
//                                     )
//                                 }

//                                 disabled={sending}

//                                 autoFocus

//                             />


//                             <button

//                                 type="submit"

//                                 className="send-button"

//                                 disabled={
//                                     sending ||
//                                     !message.trim()
//                                 }

//                             >

//                                 {sending
//                                     ? "..."
//                                     : "Send"}

//                             </button>


//                         </form>


//                     </div>

//                 ) : (

//                     <>
//                         {/* =================================================
//                             CHAT HEADER
//                         ================================================= */}

//                         <div className="chat-header">


//                             <div>

//                                 <h2>
//                                     OneDesk AI
//                                 </h2>


//                                 <span>
//                                     Online
//                                 </span>

//                             </div>


//                             {/* =============================================
//                                 NEW CHAT

//                                 IMPORTANT:
//                                 Does NOT create a MongoDB conversation.
//                             ============================================= */}

//                             <button

//                                 onClick={
//                                     startConversation
//                                 }

//                                 className="new-chat-button"

//                             >

//                                 + New Chat

//                             </button>


//                         </div>



//                         {/* =================================================
//                             ERROR
//                         ================================================= */}

//                         {error && (

//                             <div className="error-message">

//                                 {error}

//                             </div>

//                         )}



//                         {/* =================================================
//                             MESSAGES
//                         ================================================= */}

//                         <div className="messages-container">


//                             {/* Empty message state */}

//                             {messages.length === 0 && (

//                                 <div className="empty-chat">


//                                     <div className="welcome-icon">
//                                         ✨
//                                     </div>


//                                     <h3>
//                                         How can I help you?
//                                     </h3>


//                                     <p>
//                                         Ask me anything about
//                                         your organisation.
//                                     </p>


//                                 </div>

//                             )}



//                             {/* =================================================
//                                 MESSAGE LIST
//                             ================================================= */}

//                             {messages.map(
//                                 (msg, index) => (

//                                     <div

//                                         key={index}

//                                         className={
//                                             msg.sender === "user"

//                                                 ? "message user-message"

//                                                 : "message ai-message"
//                                         }

//                                     >


//                                         <div className="message-bubble">


//                                             <span className="message-sender">

//                                                 {msg.sender === "user"

//                                                     ? "You"

//                                                     : "OneDesk AI"}

//                                             </span>


//                                             <p>
//                                                 {msg.message}
//                                             </p>


//                                         </div>


//                                     </div>

//                                 )
//                             )}



//                             {/* =================================================
//                                 THINKING
//                             ================================================= */}

//                             {sending && (

//                                 <div className="message ai-message">


//                                     <div className="message-bubble">


//                                         <span className="message-sender">
//                                             OneDesk AI
//                                         </span>


//                                         <p>
//                                             Thinking...
//                                         </p>


//                                     </div>


//                                 </div>

//                             )}


//                         </div>



//                         {/* =================================================
//                             MESSAGE INPUT
//                         ================================================= */}

//                         <form

//                             className="message-input-area"

//                             onSubmit={sendMessage}

//                         >


//                             <input

//                                 type="text"

//                                 placeholder="Ask OneDesk AI..."

//                                 value={message}

//                                 onChange={(e) =>
//                                     setMessage(
//                                         e.target.value
//                                     )
//                                 }

//                                 disabled={sending}

//                             />


//                             <button

//                                 type="submit"

//                                 className="primary-button"

//                                 disabled={
//                                     sending ||
//                                     !message.trim()
//                                 }

//                             >

//                                 {sending
//                                     ? "Sending..."
//                                     : "Send"}

//                             </button>


//                         </form>


//                     </>

//                 )}


//             </main>


//         </div>

//     );

// }


// export default UserDashboard;

import { useState } from "react";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";

function UserDashboard() {
    const { user, logout } = useAuth();

    const [message, setMessage] = useState("");
    const [messages, setMessages] = useState([]);
    const [conversationId, setConversationId] = useState(null);
    const [sending, setSending] = useState(false);
    const [error, setError] = useState("");

    // ==========================================
    // CREATE CONVERSATION
    // ==========================================

    const startConversation = async () => {
        try {
            setError("");

            const response = await api.post(
                "/conversations"
            );

            setConversationId(response.data.id);

            setMessages([]);

        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to start conversation"
            );
        }
    };


    // ==========================================
    // SEND MESSAGE
    // ==========================================

    const sendMessage = async (e) => {
        e.preventDefault();

        if (!message.trim() || sending) {
            return;
        }

        try {
            setSending(true);
            setError("");

            const userMessage = message.trim();

            // Show user message immediately
            setMessages((prev) => [
                ...prev,
                {
                    sender: "user",
                    message: userMessage
                }
            ]);

            setMessage("");

            let id = conversationId;

            // Create conversation automatically
            // if one does not exist
            if (!id) {
                const conversationResponse =
                    await api.post(
                        "/conversations"
                    );

                id = conversationResponse.data.id;

                setConversationId(id);
            }

            // Send message
            const response = await api.post(
                `/conversations/${id}/messages`,
                {
                    message: userMessage
                }
            );

            // Show AI response
            setMessages((prev) => [
                ...prev,
                {
                    sender: "ai",
                    message: response.data.message
                }
            ]);

        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to send message"
            );

        } finally {
            setSending(false);
        }
    };


    return (
        <div className="user-dashboard">

            {/* ======================================
                HEADER
            ====================================== */}

            <header className="dashboard-header">

                <div>
                    <h1>
                        OneDesk AI
                    </h1>

                    <p>
                        Hello, {user?.name || "User"}
                    </p>
                </div>

                <button
                    onClick={logout}
                    className="logout-button"
                >
                    Logout
                </button>

            </header>


            {/* ======================================
                MAIN CHAT
            ====================================== */}

            <main className="chat-container">

                {!conversationId ? (

                    <div className="chat-welcome">

                        <h2>
                            Welcome to OneDesk AI
                        </h2>

                        <p>
                            Ask questions about IT, HR,
                            Finance or other departments.
                        </p>

                        <button
                            onClick={startConversation}
                            className="primary-button"
                        >
                            Start Conversation
                        </button>

                    </div>

                ) : (

                    <>

                        {/* ==================================
                            CHAT HEADER
                        ================================== */}

                        <div className="chat-header">

                            <div>

                                <h2>
                                    OneDesk AI
                                </h2>

                                <span>
                                    Online
                                </span>

                            </div>

                            <button
                                onClick={startConversation}
                                className="new-chat-button"
                            >
                                + New Chat
                            </button>

                        </div>


                        {/* ==================================
                            ERROR
                        ================================== */}

                        {error && (
                            <div className="error-message">
                                {error}
                            </div>
                        )}


                        {/* ==================================
                            MESSAGES
                        ================================== */}

                        <div className="messages-container">

                            {messages.length === 0 && (

                                <div className="empty-chat">

                                    <h3>
                                        How can I help you?
                                    </h3>

                                    <p>
                                        Ask me anything about
                                        your organisation.
                                    </p>

                                </div>

                            )}


                            {messages.map(
                                (msg, index) => (

                                    <div
                                        key={index}
                                        className={
                                            msg.sender === "user"
                                                ? "message user-message"
                                                : "message ai-message"
                                        }
                                    >

                                        <div className="message-bubble">

                                            <span className="message-sender">

                                                {msg.sender === "user"
                                                    ? "You"
                                                    : "OneDesk AI"}

                                            </span>

                                            <p>
                                                {msg.message}
                                            </p>

                                        </div>

                                    </div>

                                )
                            )}


                            {/* ==================================
                                THINKING
                            ================================== */}

                            {sending && (

                                <div className="message ai-message">

                                    <div className="message-bubble">

                                        <span className="message-sender">
                                            OneDesk AI
                                        </span>

                                        <p>
                                            Thinking...
                                        </p>

                                    </div>

                                </div>

                            )}

                        </div>


                        {/* ==================================
                            MESSAGE INPUT
                        ================================== */}

                        <form
                            className="message-input-area"
                            onSubmit={sendMessage}
                        >

                            <input
                                type="text"
                                placeholder="Ask OneDesk AI..."
                                value={message}
                                onChange={(e) =>
                                    setMessage(
                                        e.target.value
                                    )
                                }
                                disabled={sending}
                            />

                            <button
                                type="submit"
                                className="primary-button"
                                disabled={
                                    sending ||
                                    !message.trim()
                                }
                            >
                                {sending
                                    ? "Sending..."
                                    : "Send"}
                            </button>

                        </form>

                    </>

                )}

            </main>

        </div>
    );
}

export default UserDashboard;

