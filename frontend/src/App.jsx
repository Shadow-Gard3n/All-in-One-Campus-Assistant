
import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
} from "react-router-dom";

import Login from "./pages/Login";
import CreateOrganisation from "./pages/CreateOrganisation";
import JoinOrganisation from "./pages/JoinOrganisation";

import KnowledgeBase from "./pages/KnowledgeBase";

import PlatformAdminDashboard
    from "./pages/PlatformAdminDashboard";

import OrganisationAdminDashboard
    from "./pages/OrganisationAdminDashboard";

import UserDashboard
    from "./pages/UserDashboard";

import SupportDashboard
    from "./pages/SupportDashboard";


function App() {
    return (
        <BrowserRouter>

            <Routes>

                {/* -------------------------------- */}
                {/* AUTH */}
                {/* -------------------------------- */}

                <Route
                    path="/login"
                    element={<Login />}
                />

                <Route
                    path="/create-organisation"
                    element={<CreateOrganisation />}
                />

                <Route
                    path="/join-organisation"
                    element={<JoinOrganisation />}
                />


                {/* -------------------------------- */}
                {/* PLATFORM ADMIN */}
                {/* -------------------------------- */}

                <Route
                    path="/platform-admin"
                    element={<PlatformAdminDashboard />}
                />


                {/* -------------------------------- */}
                {/* ORGANISATION ADMIN */}
                {/* -------------------------------- */}
                <Route
                    path="/organisation-admin"
                    element={<OrganisationAdminDashboard />}
                />

                <Route
                    path="/organisation-admin/knowledge"
                    element={<KnowledgeBase />}
                />

                {/* <Route
                    path="/organisation-admin"
                    element={<OrganisationAdminDashboard />}
                /> */}


                {/* -------------------------------- */}
                {/* SUPPORT AGENT */}
                {/* -------------------------------- */}

                <Route
                    path="/support"
                    element={<SupportDashboard />}
                />


                {/* -------------------------------- */}
                {/* NORMAL USER */}
                {/* -------------------------------- */}

                <Route
                    path="/dashboard"
                    element={<UserDashboard />}
                />


                {/* -------------------------------- */}
                {/* DEFAULT */}
                {/* -------------------------------- */}

                <Route
                    path="*"
                    element={
                        <Navigate
                            to="/login"
                            replace
                        />
                    }
                />

            </Routes>

        </BrowserRouter>
    );
}

export default App;

