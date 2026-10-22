import { cva, type VariantProps } from "class-variance-authority";
import type * as React from "react";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// Bigface "pill": mono uppercase tag with a dot, tinted by how far a theme was checked.
export const bgBadgeVariants = cva("", {
  variants: {
    tone: {
      none: "",
      pill: "h-auto gap-[0.35rem] font-normal rounded-full border-bf-selection bg-bf-border/5 px-[0.6rem] py-[0.22rem] font-code text-[0.72rem] tracking-[0.06em] text-bf-fg-muted uppercase before:size-[5px] before:rounded-full before:bg-current before:content-['']",
      tool: "h-auto gap-[0.35rem] font-normal rounded-full border-bf-green/40 bg-bf-border/5 px-[0.6rem] py-[0.22rem] font-code text-[0.72rem] tracking-[0.06em] text-bf-green uppercase before:size-[5px] before:rounded-full before:bg-current before:content-['']",
      schema:
        "h-auto gap-[0.35rem] font-normal rounded-full border-bf-cyan/40 bg-bf-border/5 px-[0.6rem] py-[0.22rem] font-code text-[0.72rem] tracking-[0.06em] text-bf-cyan uppercase before:size-[5px] before:rounded-full before:bg-current before:content-['']",
      format:
        "h-auto gap-[0.35rem] font-normal rounded-full border-bf-burnt-orange/40 bg-bf-border/5 px-[0.6rem] py-[0.22rem] font-code text-[0.72rem] tracking-[0.06em] text-bf-burnt-orange uppercase before:size-[5px] before:rounded-full before:bg-current before:content-['']",
    },
  },
  defaultVariants: { tone: "none" },
});

export type BGBadgeProps = React.ComponentProps<typeof Badge> &
  VariantProps<typeof bgBadgeVariants>;

export function BGBadge({ tone, className, variant, ...props }: BGBadgeProps) {
  return (
    <Badge
      variant={tone && tone !== "none" ? "outline" : variant}
      className={cn(bgBadgeVariants({ tone }), className)}
      {...props}
    />
  );
}
