function DashboardLayout({ sidebar, topbar, children }) {
  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: '#f3f4f6' }}>
      {sidebar}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {topbar}
        <main style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
          {children}
        </main>
      </div>
    </div>
  );
}

export default DashboardLayout;