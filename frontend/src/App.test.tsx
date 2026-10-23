import { describe, it, expect, beforeEach, afterEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <MemoryRouter initialEntries={['/status']}>
      <QueryClientProvider client={qc}>{children}</QueryClientProvider>
    </MemoryRouter>
  )
}

describe('App', () => {
  beforeEach(() => {
    localStorage.setItem('access_token', 'mock-token')
    localStorage.setItem(
      'verifyai_user',
      JSON.stringify({
        id: '1',
        email: 'officer@aicte.gov.in',
        full_name: 'AICTE Officer',
        role: 'officer',
        is_active: true,
      })
    )
  })


  afterEach(() => {
    localStorage.clear()
  })

  it('renders the layout with the disclaimer banner', () => {
    render(<App />, {
      wrapper: ({ children }) => wrapper({ children }),
    })
    expect(
      screen.getByText(/AI-generated findings are advisory only/i)
    ).toBeInTheDocument()
  })
})

