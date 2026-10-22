import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

// Bigface variants, layered on shadcn's Button without touching components/ui/button.tsx.
// `tone` picks a Bigface look; shadcn's own `variant` / `size` still pass straight through. The BG
// classes are merged last, so on a conflict (background, padding, radius…) they win over shadcn's.
export const bgButtonVariants = cva("", {
  variants: {
    tone: {
      none: "",
      // the bright call to action: blue gradient plate, dark ink
      glow: "h-auto rounded-full bg-transparent hover:bg-transparent px-[1.15rem] py-[0.7rem] text-[0.94rem] font-semibold no-underline bg-linear-135/srgb from-bf-blue to-bf-light-blue text-ink-on-bright shadow-[0_8px_26px_color-mix(in_srgb,var(--bf-blue)_30%,transparent),inset_0_1px_0_color-mix(in_srgb,var(--bf-caret)_50%,transparent)] hover:-translate-y-0.5 hover:from-bf-light-blue hover:to-bf-pale-blue hover:text-ink-on-bright hover:shadow-[0_14px_34px_color-mix(in_srgb,var(--bf-blue)_40%,transparent),inset_0_1px_0_color-mix(in_srgb,var(--bf-caret)_60%,transparent)]",
      // quiet outline pill next to the glow button
      ghost:
        "h-auto rounded-full border-bf-selection bg-bf-border/6 px-[1.15rem] py-[0.7rem] text-[0.94rem] font-semibold text-foreground no-underline hover:border-bf-blue hover:bg-bf-blue/8 hover:text-bf-blue",
      // the small mono "copy" pill
      copy: "h-auto cursor-pointer gap-1.5 rounded-full border-bf-selection bg-bf-border/8 px-[0.6rem] py-[0.35rem] font-code text-[0.72rem] font-normal tracking-[0.04em] text-bf-fg-muted hover:border-bf-blue hover:bg-bf-blue/12 hover:text-foreground [&.done]:border-bf-lime [&.done]:text-bf-lime",
      // header link with a hairline: the GitHub call to action
      nav: "h-auto rounded-full border-bf-selection bg-transparent px-3 py-[0.4rem] text-[0.9rem] font-normal text-foreground no-underline hover:border-bf-blue hover:bg-transparent hover:text-bf-blue",
      // filter / chip that fills when aria-pressed
      chip: "h-auto cursor-pointer rounded-full border-bf-border bg-bf-border/4 px-[0.8rem] py-[0.35rem] font-code text-[0.78rem] leading-[1.65] font-normal tracking-[0.04em] text-bf-fg-muted transition-[color,border-color,background] duration-200 hover:border-bf-selection hover:bg-bf-border/4 hover:text-foreground aria-pressed:border-bf-blue aria-pressed:bg-bf-blue aria-pressed:text-ink-on-bright aria-pressed:hover:bg-bf-blue aria-pressed:hover:text-ink-on-bright",
    },
  },
  defaultVariants: { tone: "none" },
});

type ButtonProps = React.ComponentProps<typeof Button>;
export type BGButtonProps = Omit<ButtonProps, "asChild"> &
  VariantProps<typeof bgButtonVariants> & {
    /** Render as a link (shadcn's asChild + <a>), so .astro pages can pass plain text children. */
    href?: string;
  };

export function BGButton({
  tone,
  className,
  href,
  children,
  variant,
  size,
  ...props
}: BGButtonProps) {
  const classes = cn(bgButtonVariants({ tone }), className);
  // Tones sit on shadcn's default variant: it has no dark: classes, which would out-rank ours
  // (the page is <html class="dark">), and every class it sets is one a tone overrides.
  const base = tone && tone !== "none" ? "default" : variant;
  if (href !== undefined) {
    const { type: _type, ...rest } = props;
    return (
      <Button asChild variant={base} size={size} className={classes}>
        <a href={href} {...(rest as React.ComponentProps<"a">)}>
          {children}
        </a>
      </Button>
    );
  }
  return (
    <Button type="button" variant={base} size={size} className={classes} {...props}>
      {children}
    </Button>
  );
}
