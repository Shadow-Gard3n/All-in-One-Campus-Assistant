import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";

function OrganisationAdminDashboard() {
    const { user, logout } = useAuth();
    const navigate = useNavigate();
    const [dashboard, setDashboard] = useState(null);
    const [users, setUsers] = useState([]);
    const [departments, setDepartments] = useState([]);
    const [joinRequests, setJoinRequests] = useState([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    // ============================================================
    // LOAD DASHBOARD
    // ============================================================

    const loadDashboard = async () => {
        try {
            setLoading(true);
            setError("");

            const [
                dashboardResponse,
                usersResponse,
                departmentsResponse,
                requestsResponse
            ] = await Promise.all([
                api.get("/organisation-admin/dashboard"),
                api.get("/organisation-admin/users"),
                api.get("/organisation-admin/departments"),
                api.get("/organisation-admin/join-requests")
            ]);

            setDashboard(dashboardResponse.data);
            setUsers(usersResponse.data);
            setDepartments(departmentsResponse.data);
            setJoinRequests(requestsResponse.data);

        } catch (error) {
            console.error(error);

            setError(
                error.response?.data?.detail ||
                "Failed to load dashboard"
            );

        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadDashboard();
    }, []);

    // ============================================================
    // DEPARTMENT NAME
    // ============================================================

    const getDepartmentName = (departmentId) => {
        if (!departmentId) {
            return "-";
        }

        const department = departments.find(
            (item) => item.id === departmentId
        );

        return department?.name || departmentId;
    };

    // ============================================================
    // APPROVE REQUEST
    // ============================================================

    const approveRequest = async (requestId) => {
        try {
            await api.post(
                `/join-requests/${requestId}/approve`
            );

            await loadDashboard();

        } catch (error) {
            alert(
                error.response?.data?.detail ||
                "Failed to approve request"
            );
        }
    };

    // ============================================================
    // REJECT REQUEST
    // ============================================================

    const rejectRequest = async (requestId) => {
        const confirmed = window.confirm(
            "Are you sure you want to reject this request?"
        );

        if (!confirmed) {
            return;
        }

        try {
            await api.post(
                `/join-requests/${requestId}/reject`
            );

            await loadDashboard();

        } catch (error) {
            alert(
                error.response?.data?.detail ||
                "Failed to reject request"
            );
        }
    };

    // ============================================================
    // DELETE DEPARTMENT
    // ============================================================

    const deleteDepartment = async (departmentId) => {
        const confirmed = window.confirm(
            "Are you sure you want to delete this department?"
        );

        if (!confirmed) {
            return;
        }

        try {
            await api.delete(
                `/organisation-admin/departments/${departmentId}`
            );

            await loadDashboard();

        } catch (error) {
            alert(
                error.response?.data?.detail ||
                "Failed to delete department"
            );
        }
    };

    // ============================================================
    // LOADING
    // ============================================================

    if (loading) {
        return (
            <div className="dashboard-page">
                <div className="dashboard-loading">
                    Loading dashboard...
                </div>
            </div>
        );
    }

    // ============================================================
    // ERROR
    // ============================================================

    if (error) {
        return (
            <div className="dashboard-page">
                <div className="error-message">
                    {error}
                </div>
            </div>
        );
    }

    // ============================================================
    // DASHBOARD
    // ============================================================

    return (
        <div className="dashboard-page">

            {/* ================================================== */}
            {/* HEADER */}
            {/* ================================================== */}

            <header className="dashboard-header">

                <div>
                    <h1>OneDesk AI</h1>

                    <p>
                        Organisation Administration
                    </p>
                </div>

                <div className="header-user">

                    <div>
                        <strong>
                            {user?.name}
                        </strong>

                        <span>
                            Organisation Admin
                        </span>
                    </div>

                    <button
                        onClick={logout}
                        className="logout-button"
                    >
                        Logout
                    </button>

                </div>

            </header>

            {/* ================================================== */}
            {/* MAIN */}
            {/* ================================================== */}

            <main className="dashboard-content">

                {/* ================================================== */}
                {/* ORGANISATION HEADER */}
                {/* ================================================== */}

                <section className="organisation-heading">

                    <div>
                        <h2>
                            {dashboard?.organisation?.name}
                        </h2>

                        <p>
                            Manage your organisation,
                            members and departments.
                        </p>
                    </div>

                    <span className="status-badge">
                        {dashboard?.organisation?.status}
                    </span>

                </section>

                {/* ================================================== */}
                {/* STATISTICS */}
                {/* ================================================== */}

                <section className="stats-grid">

                    <div className="stat-card">
                        <span>Users</span>

                        <strong>
                            {dashboard?.stats?.users || 0}
                        </strong>
                    </div>

                    <div className="stat-card">
                        <span>Support Agents</span>

                        <strong>
                            {dashboard?.stats?.support_agents || 0}
                        </strong>
                    </div>

                    <div className="stat-card">
                        <span>Departments</span>

                        <strong>
                            {dashboard?.stats?.departments || 0}
                        </strong>
                    </div>

                    <div className="stat-card">
                        <span>Pending Requests</span>

                        <strong>
                            {dashboard?.stats?.pending_requests || 0}
                        </strong>
                    </div>

                </section>

                {/* ================================================== */}
                {/* JOIN REQUESTS */}
                {/* ================================================== */}

                <section className="dashboard-section">

                    <div className="section-header">

                        <div>
                            <h2>
                                Join Requests
                            </h2>

                            <p>
                                Review people requesting
                                access to your organisation.
                            </p>
                        </div>

                    </div>

                    {joinRequests.length === 0 ? (

                        <div className="empty-state">
                            No pending join requests.
                        </div>

                    ) : (

                        <div className="table-container">

                            <table>

                                <thead>
                                    <tr>
                                        <th>Name</th>
                                        <th>Email</th>
                                        <th>Role</th>
                                        <th>Department</th>
                                        <th>Actions</th>
                                    </tr>
                                </thead>

                                <tbody>

                                    {joinRequests.map((request) => (

                                        <tr key={request.id}>

                                            <td>
                                                {request.user?.name ||
                                                    "Unknown"}
                                            </td>

                                            <td>
                                                {request.user?.email ||
                                                    "-"}
                                            </td>

                                            <td>
                                                <span className="role-badge">
                                                    {request.requested_role}
                                                </span>
                                            </td>

                                            <td>
                                                {getDepartmentName(
                                                    request.department_id
                                                )}
                                            </td>

                                            <td>

                                                <div className="action-buttons">

                                                    <button
                                                        className="approve-button"
                                                        onClick={() =>
                                                            approveRequest(
                                                                request.id
                                                            )
                                                        }
                                                    >
                                                        Approve
                                                    </button>

                                                    <button
                                                        className="reject-button"
                                                        onClick={() =>
                                                            rejectRequest(
                                                                request.id
                                                            )
                                                        }
                                                    >
                                                        Reject
                                                    </button>

                                                </div>

                                            </td>

                                        </tr>

                                    ))}

                                </tbody>

                            </table>

                        </div>

                    )}

                </section>

                {/* ================================================== */}
                {/* USERS */}
                {/* ================================================== */}

                <section className="dashboard-section">

                    <div className="section-header">

                        <div>
                            <h2>
                                Organisation Members
                            </h2>

                            <p>
                                All users and support agents
                                belonging to your organisation.
                            </p>
                        </div>

                    </div>

                    <div className="table-container">

                        <table>

                            <thead>

                                <tr>
                                    <th>Name</th>
                                    <th>Email</th>
                                    <th>Role</th>
                                    <th>Department</th>
                                    <th>Status</th>
                                </tr>

                            </thead>

                            <tbody>

                                {users.length === 0 ? (

                                    <tr>
                                        <td colSpan="5">
                                            No organisation members.
                                        </td>
                                    </tr>

                                ) : (

                                    users.map((member) => (

                                        <tr key={member.id}>

                                            <td>
                                                {member.name}
                                            </td>

                                            <td>
                                                {member.email}
                                            </td>

                                            <td>
                                                <span className="role-badge">
                                                    {member.role}
                                                </span>
                                            </td>

                                            <td>
                                                {getDepartmentName(
                                                    member.department_id
                                                )}
                                            </td>

                                            <td>
                                                {member.is_active
                                                    ? "Active"
                                                    : "Inactive"}
                                            </td>

                                        </tr>

                                    ))

                                )}

                            </tbody>

                        </table>

                    </div>

                </section>

                {/* ================================================== */}
                {/* DEPARTMENTS */}
                {/* ================================================== */}

                <section className="dashboard-section">

                    <div className="section-header">

                        <div>
                            <h2>
                                Departments
                            </h2>

                            <p>
                                Manage departments and
                                department settings.
                            </p>
                        </div>
                        <div className="action-buttons">

                            <button
                                className="primary-button"
                                onClick={() =>
                                    alert(
                                        "Department creation UI will be added next."
                                    )
                                }
                            >
                                + Add Department
                            </button>

                            <button
                                className="secondary-small-button"
                                onClick={() =>
                                    navigate("/organisation-admin/knowledge")
                                }
                            >
                                Knowledge Base
                            </button>

                        </div>

                        {/* <button
                            className="primary-button"
                            onClick={() =>
                                alert(
                                    "Department creation UI will be added next."
                                )
                            }
                        >
                            + Add Department
                        </button> */}

                    </div>

                    <div className="department-grid">

                        {departments.length === 0 ? (

                            <div className="empty-state">
                                No departments found.
                            </div>

                        ) : (

                            departments.map((department) => (

                                <div
                                    className="department-card"
                                    key={department.id}
                                >

                                    <div>

                                        <h3>
                                            {department.name}
                                        </h3>

                                        <p>
                                            Bot:{" "}
                                            {department.bot_enabled
                                                ? "Enabled"
                                                : "Disabled"}
                                        </p>

                                        <p>
                                            Human Support:{" "}
                                            {department.human_support_enabled
                                                ? "Enabled"
                                                : "Disabled"}
                                        </p>

                                    </div>

                                    <div className="action-buttons">

                                        <button
                                            className="secondary-small-button"
                                            onClick={() =>
                                                alert(
                                                    "Department editing UI will be added next."
                                                )
                                            }
                                        >
                                            Edit
                                        </button>

                                        <button
                                            className="danger-small-button"
                                            onClick={() =>
                                                deleteDepartment(
                                                    department.id
                                                )
                                            }
                                        >
                                            Delete
                                        </button>

                                    </div>

                                </div>

                            ))

                        )}

                    </div>

                </section>

            </main>

        </div>
    );
}

export default OrganisationAdminDashboard;