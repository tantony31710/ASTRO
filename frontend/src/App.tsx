import { Routes, Route } from "react-router-dom";
import Sidebar from "./components/Sidebar";
import StoragePage from "./pages/StoragePage";
import MediaPage from "./pages/MediaPage";
import ModelsPage from "./pages/ModelsPage";
import ChatPage from "./pages/ChatPage";

export default function App() {
  return (
    <div className="app-shell">
      <Sidebar />
      <main className="main">
        <Routes>
          <Route path="/" element={<StoragePage />} />
          <Route path="/media" element={<MediaPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/chat" element={<ChatPage />} />
        </Routes>
      </main>
    </div>
  );
}
