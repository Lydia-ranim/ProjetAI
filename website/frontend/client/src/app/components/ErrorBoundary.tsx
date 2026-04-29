import React from 'react';

export default class ErrorBoundary extends React.Component<{children: React.ReactNode}, {hasError: boolean, error: Error | null}> {
  constructor(props: {children: React.ReactNode}) {
    super(props);
    this.state = { hasError: false, error: null };
  }
  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center text-red-500">
          <h2>Something went wrong.</h2>
          <pre className="text-sm mt-4 text-left p-4 bg-red-950 rounded">{this.state.error?.message}</pre>
          <button className="mt-4 px-4 py-2 bg-red-800 text-white rounded" onClick={() => window.location.reload()}>Reload App</button>
        </div>
      );
    }
    return this.props.children;
  }
}
