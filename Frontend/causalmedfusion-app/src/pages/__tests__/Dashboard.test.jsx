import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import Dashboard from '../Dashboard';

// Mock child components to isolate Dashboard layout and avoid deep dependencies
vi.mock('../../components/Topbar', () => ({
  default: () => <div data-testid="mock-topbar">Topbar</div>
}));
vi.mock('../../components/StatsCards', () => ({
  default: () => <div data-testid="mock-statscards">StatsCards</div>
}));
vi.mock('../../components/PatientTable', () => ({
  default: () => <div data-testid="mock-patienttable">PatientTable</div>
}));

describe('Dashboard Component', () => {
  it('renders the core dashboard layout elements', () => {
    render(
      <MemoryRouter>
        <Dashboard />
      </MemoryRouter>
    );

    expect(screen.getByTestId('mock-topbar')).toBeInTheDocument();
    expect(screen.getByTestId('mock-statscards')).toBeInTheDocument();
    expect(screen.getByTestId('mock-patienttable')).toBeInTheDocument();
  });
});
