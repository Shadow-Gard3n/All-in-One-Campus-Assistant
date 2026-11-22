import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

function KnowledgeBase() {
    const navigate = useNavigate();

    const [departments, setDepartments] = useState([]);
    const [documents, setDocuments] = useState([]);

    const [selectedDepartment, setSelectedDepartment] = useState("");
    const [selectedFile, setSelectedFile] = useState(null);

    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);
    const [error, setError] = useState("");

    // ============================================================
    // LOAD DEPARTMENTS
    // ============================================================

    const loadDepartments = async () => {
        try {
            const response = await api.get(
                "/organisation-admin/departments"
            );

            setDepartments(response.data);

            if (response.data.length > 0) {
                setSelectedDepartment(response.data[0].id);
            }
        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to load departments"
            );
        }
    };

    // ============================================================
    // LOAD DOCUMENTS
    // ============================================================

    const loadDocuments = async (departmentId = "") => {
        try {
            const params = departmentId
                ? { department_id: departmentId }
                : {};

            const response = await api.get(
                "/knowledge/documents",
                { params }
            );

            setDocuments(response.data);
        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to load documents"
            );
        }
    };

    // ============================================================
    // INITIAL LOAD
    // ============================================================

    useEffect(() => {
        const loadData = async () => {
            try {
                setLoading(true);
                setError("");

                await loadDepartments();
            } finally {
                setLoading(false);
            }
        };

        loadData();
    }, []);

    // ============================================================
    // LOAD DOCUMENTS WHEN DEPARTMENT CHANGES
    // ============================================================

    useEffect(() => {
        if (selectedDepartment) {
            loadDocuments(selectedDepartment);
        }
    }, [selectedDepartment]);

    // ============================================================
    // UPLOAD DOCUMENT
    // ============================================================

    const uploadDocument = async () => {
        if (!selectedDepartment) {
            alert("Please select a department.");
            return;
        }

        if (!selectedFile) {
            alert("Please select a file.");
            return;
        }

        const allowedTypes = [
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain"
        ];

        if (!allowedTypes.includes(selectedFile.type)) {
            alert("Only PDF, DOCX and TXT files are allowed.");
            return;
        }

        const maxSize = 50 * 1024 * 1024;

        if (selectedFile.size > maxSize) {
            alert("File size cannot exceed 50 MB.");
            return;
        }

        try {
            setUploading(true);
            setError("");

            const formData = new FormData();

            formData.append(
                "department_id",
                selectedDepartment
            );

            formData.append(
                "file",
                selectedFile
            );

            await api.post(
                "/knowledge/documents",
                formData,
                {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(
                            "access_token"
                        )}`,
                        "Content-Type": "multipart/form-data"
                    }
                }
            );

            alert("Document uploaded successfully.");

            setSelectedFile(null);

            // Reset file input
            const fileInput =
                document.getElementById("knowledge-file-input");

            if (fileInput) {
                fileInput.value = "";
            }

            await loadDocuments(selectedDepartment);

        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to upload document"
            );
        } finally {
            setUploading(false);
        }
    };

    // ============================================================
    // DELETE DOCUMENT
    // ============================================================

    const deleteDocument = async (documentId) => {
        const confirmed = window.confirm(
            "Are you sure you want to delete this document?"
        );

        if (!confirmed) {
            return;
        }

        try {
            await api.delete(
                `/knowledge/documents/${documentId}`,
                {
                    headers: {
                        Authorization: `Bearer ${localStorage.getItem(
                            "access_token"
                        )}`
                    }
                }
            );

            await loadDocuments(selectedDepartment);

        } catch (error) {
            console.error(error);

            alert(
                error.response?.data?.detail ||
                "Failed to delete document"
            );
        }
    };

    // ============================================================
    // FORMAT FILE SIZE
    // ============================================================

    const formatFileSize = (bytes) => {
        if (bytes < 1024) {
            return `${bytes} B`;
        }

        if (bytes < 1024 * 1024) {
            return `${(bytes / 1024).toFixed(1)} KB`;
        }

        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    };

    // ============================================================
    // LOADING
    // ============================================================

    if (loading) {
        return (
            <div className="dashboard-page">
                <div className="dashboard-loading">
                    Loading knowledge base...
                </div>
            </div>
        );
    }

    // ============================================================
    // UI
    // ============================================================

    return (
        <div className="dashboard-page">

            {/* HEADER */}

            <header className="dashboard-header">

                <div>
                    <h1>OneDesk AI</h1>

                    <p>
                        Organisation Knowledge Base
                    </p>
                </div>

                <button
                    className="secondary-small-button"
                    onClick={() =>
                        navigate("/organisation-admin")
                    }
                >
                    ← Back to Dashboard
                </button>

            </header>

            <main className="dashboard-content">

                {/* TITLE */}

                <section className="organisation-heading">

                    <div>
                        <h2>Knowledge Base</h2>

                        <p>
                            Upload documents that your organisation's
                            AI assistants can use to answer questions.
                        </p>
                    </div>

                </section>

                {/* ERROR */}

                {error && (
                    <div className="error-message">
                        {error}
                    </div>
                )}

                {/* UPLOAD SECTION */}

                <section className="dashboard-section">

                    <div className="section-header">

                        <div>
                            <h2>
                                Upload Knowledge
                            </h2>

                            <p>
                                Add PDF, DOCX or TXT documents
                                for a department.
                            </p>
                        </div>

                    </div>

                    <div className="knowledge-upload-card">

                        {/* DEPARTMENT */}

                        <div className="form-group">

                            <label>
                                Department
                            </label>

                            <select
                                value={selectedDepartment}
                                onChange={(e) =>
                                    setSelectedDepartment(
                                        e.target.value
                                    )
                                }
                            >
                                <option value="">
                                    Select department
                                </option>

                                {departments.map(
                                    (department) => (
                                        <option
                                            key={department.id}
                                            value={department.id}
                                        >
                                            {department.name}
                                        </option>
                                    )
                                )}
                            </select>

                        </div>

                        {/* FILE */}

                        <div className="form-group">

                            <label>
                                Document
                            </label>

                            <input
                                id="knowledge-file-input"
                                type="file"
                                accept=".pdf,.docx,.txt"
                                onChange={(e) =>
                                    setSelectedFile(
                                        e.target.files?.[0] ||
                                        null
                                    )
                                }
                            />

                            <small>
                                Maximum size: 50 MB
                                <br />
                                Allowed: PDF, DOCX, TXT
                            </small>

                        </div>

                        {/* SELECTED FILE */}

                        {selectedFile && (
                            <div className="selected-file">

                                <strong>
                                    Selected:
                                </strong>{" "}

                                {selectedFile.name}

                                <span>
                                    {" "}
                                    (
                                    {formatFileSize(
                                        selectedFile.size
                                    )}
                                    )
                                </span>

                            </div>
                        )}

                        {/* UPLOAD */}

                        <button
                            className="primary-button"
                            onClick={uploadDocument}
                            disabled={uploading}
                        >
                            {uploading
                                ? "Uploading..."
                                : "Upload Document"}
                        </button>

                    </div>

                </section>

                {/* DOCUMENTS */}

                <section className="dashboard-section">

                    <div className="section-header">

                        <div>
                            <h2>
                                Department Documents
                            </h2>

                            <p>
                                Documents currently available
                                to this department's AI skill.
                            </p>
                        </div>

                    </div>

                    {documents.length === 0 ? (

                        <div className="empty-state">
                            No documents uploaded for this
                            department yet.
                        </div>

                    ) : (

                        <div className="table-container">

                            <table>

                                <thead>

                                    <tr>
                                        <th>Filename</th>
                                        <th>Type</th>
                                        <th>Size</th>
                                        <th>Status</th>
                                        <th>Actions</th>
                                    </tr>

                                </thead>

                                <tbody>

                                    {documents.map(
                                        (document) => (

                                            <tr
                                                key={
                                                    document.id
                                                }
                                            >

                                                <td>
                                                    {document.filename}
                                                </td>

                                                <td>
                                                    {document.file_type.toUpperCase()}
                                                </td>

                                                <td>
                                                    {formatFileSize(
                                                        document.file_size
                                                    )}
                                                </td>

                                                <td>

                                                    <span className="status-badge">
                                                        {
                                                            document.status
                                                        }
                                                    </span>

                                                </td>

                                                <td>

                                                    <button
                                                        className="danger-small-button"
                                                        onClick={() =>
                                                            deleteDocument(
                                                                document.id
                                                            )
                                                        }
                                                    >
                                                        Delete
                                                    </button>

                                                </td>

                                            </tr>

                                        )
                                    )}

                                </tbody>

                            </table>

                        </div>

                    )}

                </section>

            </main>

        </div>
    );
}

export default KnowledgeBase;