import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, it, expect, vi } from 'vitest';
import Login from '../Login';
import * as authService from '../../auth/authService';

// Mock the auth module since it uses Axios
vi.mock('../../auth/authService', () => ({
  login: vi.fn(),
}));

describe('Login Component', () => {
  it('renders login form properly', () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    expect(screen.getByRole('heading', { name: /login/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/enter username:/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/enter password:/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument();
  });

  it('displays an error if login throws', async () => {
    // Mock login failure
    authService.login.mockRejectedValueOnce(new Error('Invalid credentials'));

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>
    );

    const userInp = screen.getByLabelText(/enter username:/i);
    const passInp = screen.getByLabelText(/enter password:/i);
    const submitBtn = screen.getByRole('button', { name: /login/i });

    fireEvent.change(userInp, { target: { value: 'testuser' } });
    fireEvent.change(passInp, { target: { value: 'wrongpass' } });
    fireEvent.click(submitBtn);

    // After async mock returns
    const errorMsg = await screen.findByText(/invalid username or password/i);
    expect(errorMsg).toBeInTheDocument();
  });
});
