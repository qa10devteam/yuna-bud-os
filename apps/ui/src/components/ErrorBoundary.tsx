'use client';

import { Component, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props { children: ReactNode; fallback?: ReactNode; resetKey?: string; }
interface State { hasError: boolean; error?: Error; }

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  componentDidUpdate(prevProps: Props) {
    // Resetuj boundary automatycznie gdy zmienia się strona
    if (this.state.hasError && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ hasError: false, error: undefined });
    }
  }
  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="min-h-screen bg-earth-950 flex items-center justify-center p-6">
          <div className="flex flex-col items-center gap-5 max-w-sm w-full text-center">
            <div className="w-16 h-16 rounded-2xl bg-accent-danger/10 border border-accent-danger/20 flex items-center justify-center">
              <AlertTriangle className="w-8 h-8 text-accent-danger" />
            </div>
            <div className="space-y-1.5">
              <h2 className="text-xl font-bold text-earth-100">Coś poszło nie tak</h2>
              <p className="text-earth-400 text-sm">Spróbuj odświeżyć stronę</p>
            </div>
            {this.state.error?.message && (
              <p className="text-xs text-earth-600 font-mono px-4 py-2.5 bg-earth-900/60 border border-earth-800/60 rounded-token w-full text-left break-words">
                {this.state.error.message}
              </p>
            )}
            <button
              onClick={() => this.setState({ hasError: false })}
              className="btn-primary gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Odśwież
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
