import React from "react";

const Layout = ({ children }: { children: React.ReactNode }) => {
  return (
    <div className="flex flex-col min-h-screen">
      {/* Header – Air NZ branding */}
      <header className="bg-anr-primary text-white py-4 shadow-md">
        <div className="container mx-auto flex items-center justify-between px-4">
          <h1 className="text-2xl font-semibold">FlightOps</h1>
          {/* Optional Air NZ logo – replace with actual asset */}
          {/* <img src="/logo-anr.svg" alt="Air NZ logo" className="h-8" /> */}
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 container mx-auto px-4 py-6">{children}</main>

      {/* Footer – dark background */}
      <footer className="bg-anr-dark text-anr-light py-3">
        <div className="container mx-auto text-center text-sm">
          © {new Date().getFullYear()} Air New Zealand-styled FlightOps
        </div>
      </footer>
    </div>
  );
};

export default Layout;