import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "../../lib/utils"

// Buton varyantları ve boyutları için stil tanımları
const buttonVariants = cva(
  "inline-flex items-center justify-center rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 ring-offset-background",
  {
    variants: {
      variant: {
        // Karanlık tema uyumlu buton stili
        dark: "dark:bg-gray-800 dark:text-white dark:hover:bg-gray-700",
        // Varsayılan buton stili
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        // Yıkıcı eylemler için buton stili
        destructive: "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        // Sınır çizgili buton stili
        outline: "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        // İkincil buton stili
        secondary: "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        // Gölgeli buton stili
        ghost: "hover:bg-accent hover:text-accent-foreground",
        // Link gibi görünen buton stili
        link: "underline-offset-4 hover:underline text-primary",
      },
      size: {
        // Varsayılan boyut
        default: "h-10 px-4 py-2",
        // Küçük boyut
        sm: "h-9 px-3 rounded-md",
        // Büyük boyut
        lg: "h-11 px-8 rounded-md",
        // İkon buton boyutu
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {}

// Tek sorumluluğu buton render etmek olan temel bileşen
const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

// Storybook ve test senaryolarında kullanılacak ikon destekli buton
export interface ButtonIconProps extends ButtonProps {
  iconLeft?: React.ReactNode
  iconRight?: React.ReactNode
}

export const IconButton = React.forwardRef<HTMLButtonElement, ButtonIconProps>(
  ({ iconLeft, iconRight, children, className, ...props }, ref) => (
    <Button ref={ref} className={cn("gap-2", className)} {...props}>
      {iconLeft}
      {children}
      {iconRight}
    </Button>
  )
)
IconButton.displayName = "IconButton"

export { Button, buttonVariants }
