import React from "react"
import { render, screen } from "@testing-library/react"
import "@testing-library/jest-dom"
import { Button } from "../button"

// Button bileşeni için temel testler
describe("Button", () => {
  it("renders default variant", () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole("button", { name: /click me/i })).toBeInTheDocument()
  })

  it("applies variant and size", () => {
    render(
      <Button variant="secondary" size="lg">
        Large
      </Button>
    )
    const btn = screen.getByRole("button")
    expect(btn).toHaveClass("bg-secondary")
    expect(btn).toHaveClass("h-11")
  })

  it("renders disabled state", () => {
    render(<Button disabled>Disabled</Button>)
    expect(screen.getByRole("button")).toBeDisabled()
  })
})
