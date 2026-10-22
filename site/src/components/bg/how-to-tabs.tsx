import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import type { HowToCard, HowToTab } from "../../data/how-to";
import { BGButton } from "./button.tsx";

// The pill row borrows bigface's install-tabs styling. Radix marks the selected trigger with
// data-state="active" (not a bare data-active attribute), so the selected look keys off that.
const trigger =
  "h-auto flex-none cursor-pointer rounded-full border-0 px-[0.85rem] py-[0.4rem] text-[0.82rem] leading-[1.65] font-medium text-bf-fg-muted transition-[color,background] duration-200 hover:text-foreground dark:text-bf-fg-muted dark:hover:text-foreground data-[state=active]:bg-linear-135/srgb data-[state=active]:from-bf-pale-blue data-[state=active]:to-bf-blue data-[state=active]:text-ink-on-bright dark:data-[state=active]:bg-linear-135/srgb dark:data-[state=active]:text-ink-on-bright dark:data-[state=active]:hover:text-ink-on-bright group-data-[variant=default]/tabs-list:data-[state=active]:shadow-[0_6px_18px_color-mix(in_srgb,var(--bf-blue)_30%,transparent)]";

function HowToCardPlate({ card }: { card: HowToCard }) {
  return (
    <article
      data-howto-card={card.id}
      className="overflow-hidden rounded-[16px] border border-bf-border bg-bf-border-muted/70"
    >
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 px-3 pt-[0.6rem] pb-2">
        <div className="flex min-w-0 flex-wrap items-baseline gap-x-2">
          <span className="font-code text-[0.8rem] text-foreground">{card.title}</span>
          {card.path && <span className="font-code text-[0.68rem] text-bf-dim">{card.path}</span>}
        </div>
        {card.code && (
          <BGButton
            tone="copy"
            className="ml-auto"
            data-copy={card.code}
            data-swap="off"
            aria-label={"Copy the " + card.title + " snippet"}
          >
            copy
          </BGButton>
        )}
      </header>
      {card.steps && (
        <ol
          data-howto-steps={card.id}
          className="mt-0 mb-3 grid list-decimal gap-1 pr-3 pl-[2rem] text-[0.84rem] text-bf-fg-muted marker:font-bold marker:text-bf-lime"
        >
          {card.steps.map((step) => (
            <li key={step} className="pl-1">
              {step}
            </li>
          ))}
        </ol>
      )}
      {card.code && (
        <pre
          data-howto-code={card.id}
          className="m-0 max-h-[420px] overflow-x-auto rounded-none border-x-0 border-b-0 border-t border-bf-border bg-bf-border-muted/85 px-3 py-[0.85rem] text-[0.9rem] leading-[1.6]"
        >
          <code>{card.code}</code>
        </pre>
      )}
      {card.note && (
        <p
          data-howto-note={card.id}
          className="m-0 border-t border-bf-border/70 px-3 py-2 text-[0.78rem] text-bf-dim"
        >
          {card.note}
        </p>
      )}
    </article>
  );
}

// Four routes into the family, one island. Panels are force-mounted so every snippet is in the
// static HTML (and every copy button works before hydration); inactive panels are hidden.
export function BGHowToTabs({ tabs }: { tabs: HowToTab[] }) {
  return (
    <Tabs defaultValue={tabs[0]?.id} className="gap-0">
      <TabsList
        aria-label="How to use QuBlack"
        data-howto-tabs
        className="flex w-full flex-wrap justify-start gap-[0.4rem] rounded-full border border-bf-border bg-bf-border-muted/55 p-[0.4rem] group-data-horizontal/tabs:h-auto"
      >
        {tabs.map((tab) => (
          <TabsTrigger key={tab.id} value={tab.id} data-howto-tab={tab.id} className={trigger}>
            {tab.label}
          </TabsTrigger>
        ))}
      </TabsList>
      {tabs.map((tab) => (
        <TabsContent
          key={tab.id}
          value={tab.id}
          forceMount
          className="mt-[0.9rem] data-[state=inactive]:hidden"
        >
          <p className="m-0 max-w-[68ch] text-[0.9rem] text-bf-fg-muted" data-howto-blurb={tab.id}>
            {tab.blurb}
          </p>
          <div className="mt-3 grid gap-3" data-howto-panel={tab.id}>
            {tab.cards.map((card) => (
              <HowToCardPlate key={card.id} card={card} />
            ))}
          </div>
        </TabsContent>
      ))}
    </Tabs>
  );
}
