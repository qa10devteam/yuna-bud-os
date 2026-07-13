'use client';
export default function OfflinePage() {
  return (
    <div className="min-h-screen bg-earth-950 flex items-center justify-center">
      <div className="text-center">
        <div className="text-6xl mb-4">📡</div>
        <h1 className="text-earth-100 text-2xl font-semibold mb-2">Brak połączenia</h1>
        <p className="text-earth-400">Sprawdź połączenie internetowe i spróbuj ponownie.</p>
        <button onClick={() => window.location.reload()} className="btn-primary mt-6">
          Odśwież
        </button>
      </div>
    </div>
  );
}
