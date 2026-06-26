export default function UploadToolbar({
  uploading,
  loading,
  handleUpload,
  handleRefresh,
}) {
  return (
    <div
      style={{
        background: "white",
        padding: "1.25rem",
        borderRadius: "10px",
        marginBottom: "1.5rem",
        boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
      }}
    >
      <div
        style={{
          display: "flex",
          gap: ".75rem",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <input
          id="file-upload"
          type="file"
          accept=".pdf,.mp3,.mp4,.wav,.m4a,.ogg"
          onChange={handleUpload}
          disabled={uploading}
          style={{ display: "none" }}
        />

        <label
          htmlFor="file-upload"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: ".5rem",
            padding: ".6rem 1.2rem",
            background: uploading ? "#9ca3af" : "#2563eb",
            color: "white",
            borderRadius: "8px",
            cursor: uploading ? "not-allowed" : "pointer",
            fontWeight: 500,
          }}
        >
          {uploading ? "⏳ Processing..." : "📁 Upload File"}
        </label>

        <button
          onClick={handleRefresh}
          disabled={loading || uploading}
          style={{
            padding: ".6rem 1rem",
            background:
              loading || uploading ? "#9ca3af" : "#6b7280",
            color: "white",
            border: "none",
            borderRadius: "8px",
            cursor:
              loading || uploading
                ? "not-allowed"
                : "pointer",
          }}
        >
          🔄 Refresh
        </button>

        <span
          style={{
            fontSize: ".9rem",
            color: "#6b7280",
          }}
        >
          Supports: PDF, MP3, MP4, WAV
        </span>
      </div>
    </div>
  );
}