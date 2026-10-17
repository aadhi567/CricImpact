import React from 'react';
import { AlertTriangle, RotateCcw } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
    if (this.props.onReset) {
      this.props.onReset();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="w-full bg-[#161616] rounded-xl p-8 border border-[#4D2626] text-center space-y-4 my-6 font-sans">
          <div className="inline-flex p-3 rounded-full bg-[#271414] text-[#C25454] border border-[#4D2626]">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-[#F2F2F2]">
              {this.props.title || 'An unexpected rendering error occurred'}
            </h2>
            <p className="text-xs text-[#858585] mt-1 max-w-lg mx-auto">
              {this.state.error?.message || 'The component failed to render. You can try refreshing or resetting the view.'}
            </p>
          </div>
          <div className="flex justify-center gap-3 pt-2">
            <button
              type="button"
              onClick={this.handleReset}
              className="px-4 py-2 bg-[#D4AF57] hover:bg-[#E1C878] text-[#080808] font-bold text-xs rounded-lg transition-colors flex items-center gap-1.5 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Retry Render</span>
            </button>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="px-4 py-2 bg-[#1A1A1A] hover:bg-[#222222] border border-[#2D2D2D] hover:border-[#D4AF57] text-[#F2F2F2] text-xs font-semibold rounded-lg transition-colors cursor-pointer"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
