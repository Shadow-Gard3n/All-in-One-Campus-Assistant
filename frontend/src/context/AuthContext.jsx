import { createContext, useContext, useEffect, useState } from "react";
import api from "../services/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
    const [token, setToken] = useState(
        localStorage.getItem("access_token")
    );

    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    // --------------------------------------------------
    // Load logged-in user when app starts
    // --------------------------------------------------

    useEffect(() => {
        const loadUser = async () => {
            if (!token) {
                setLoading(false);
                return;
            }

            try {
                const response = await api.get("/auth/me");

                setUser(response.data);
            } catch (error) {
                console.error("Authentication failed:", error);

                localStorage.removeItem("access_token");

                setToken(null);
                setUser(null);
            } finally {
                setLoading(false);
            }
        };

        loadUser();
    }, [token]);

    // --------------------------------------------------
    // Login
    // --------------------------------------------------

    const login = async (email, password) => {
        // 1. Login
        const response = await api.post("/auth/login", {
            email,
            password,
        });

        // 2. Get JWT
        const accessToken = response.data.access_token;

        // 3. Save JWT
        localStorage.setItem(
            "access_token",
            accessToken
        );

        setToken(accessToken);

        // 4. Get current user
        // Use the token explicitly here because React
        // state update above is asynchronous.
        const userResponse = await api.get("/auth/me", {
            headers: {
                Authorization: `Bearer ${accessToken}`,
            },
        });

        const loggedInUser = userResponse.data;

        // 5. Store user
        setUser(loggedInUser);

        // 6. Return user to Login.jsx
        return loggedInUser;
    };

    // --------------------------------------------------
    // Register
    // --------------------------------------------------

    const register = async ({
        name,
        email,
        password,
        organisation_id,
        role,
        department_id,
    }) => {
        const response = await api.post(
            "/auth/register",
            {
                name,
                email,
                password,

                organisation_id,

                role,

                // Normal user → null
                // Support agent → selected department
                department_id:
                    role === "support_agent"
                        ? department_id
                        : null,
            }
        );

        return response.data;
    };

    // --------------------------------------------------
    // Logout
    // --------------------------------------------------

    const logout = () => {
        localStorage.removeItem("access_token");

        setToken(null);
        setUser(null);
    };

    // --------------------------------------------------
    // Context value
    // --------------------------------------------------

    const value = {
        token,
        user,
        loading,

        login,
        register,
        logout,

        isAuthenticated: !!token,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    return useContext(AuthContext);
}