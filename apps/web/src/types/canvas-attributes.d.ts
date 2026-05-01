export {};

// Extend HTML div to allow the `zone`, `layer`, `size` attributes used by design-system.css
declare module "react" {
  interface HTMLAttributes<T> {
    zone?: string;
    layer?: string;
    size?: string;
  }
}
