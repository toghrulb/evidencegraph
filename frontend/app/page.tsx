const foundationItems = [
  {
    eyebrow: "Interface",
    title: "A focused research surface",
    description:
      "A responsive Next.js shell creates a clear starting point for the evidence workspace.",
  },
  {
    eyebrow: "Service boundary",
    title: "Independent, typed applications",
    description:
      "Frontend and API concerns stay separate so each side can evolve and be verified on its own.",
  },
  {
    eyebrow: "Local platform",
    title: "Reproducible infrastructure",
    description:
      "Containerized services make the foundation consistent across development and continuous integration.",
  },
] as const;

export default function HomePage() {
  return (
    <>
      <a
        className="fixed left-4 top-4 z-50 -translate-y-24 rounded-md bg-[var(--foreground)] px-4 py-2 text-sm font-semibold text-[var(--background)] transition-transform focus:translate-y-0 focus:outline-none focus:ring-2 focus:ring-[var(--accent)] focus:ring-offset-2"
        href="#main-content"
      >
        Skip to content
      </a>

      <div className="relative min-h-screen overflow-hidden bg-[var(--background)] text-[var(--foreground)]">
        <div
          className="pointer-events-none absolute inset-0 dot-grid"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -right-32 -top-44 size-[34rem] rounded-full bg-[var(--glow)] blur-3xl"
          aria-hidden="true"
        />

        <header className="relative mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-6 sm:px-8 lg:px-10">
          <div
            className="flex items-center gap-3"
            aria-label="EvidenceGraph home"
          >
            <span
              className="grid size-9 place-items-center rounded-lg border border-[var(--line-strong)] bg-[var(--panel)] text-xs font-bold tracking-[0.16em] text-[var(--accent-strong)] shadow-sm"
              aria-hidden="true"
            >
              EG
            </span>
            <span className="text-sm font-semibold tracking-tight">
              EvidenceGraph
            </span>
          </div>

          <div
            className="flex items-center gap-2 rounded-full border border-[var(--line)] bg-[var(--panel)] px-3 py-1.5 text-xs font-medium text-[var(--muted)] shadow-sm backdrop-blur"
            aria-label="Project status: Phase 0 foundation"
          >
            <span
              className="size-1.5 rounded-full bg-[var(--accent)]"
              aria-hidden="true"
            />
            Phase 0 · Foundation
          </div>
        </header>

        <main
          id="main-content"
          className="relative mx-auto w-full max-w-6xl px-6 pb-16 pt-16 sm:px-8 sm:pt-24 lg:px-10 lg:pb-24 lg:pt-28"
        >
          <section className="max-w-4xl" aria-labelledby="hero-title">
            <p className="mb-6 text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent-strong)]">
              Evidence-led research intelligence
            </p>
            <h1
              id="hero-title"
              className="max-w-4xl text-balance text-5xl font-semibold leading-[1.04] tracking-[-0.04em] sm:text-6xl lg:text-7xl"
            >
              Research answers should be easy to verify.
            </h1>
            <p className="mt-7 max-w-2xl text-pretty text-lg leading-8 text-[var(--muted)] sm:text-xl">
              EvidenceGraph is being built to connect technical conclusions to
              inspectable source evidence. This foundation establishes the
              dependable platform that the research workflow will grow on.
            </p>

            <div className="mt-9 flex w-fit flex-wrap items-center gap-x-3 gap-y-2 rounded-xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3 text-sm shadow-sm backdrop-blur">
              <span className="font-semibold text-[var(--accent-strong)]">
                Foundation ready
              </span>
              <span
                className="h-4 w-px bg-[var(--line-strong)]"
                aria-hidden="true"
              />
              <span className="text-[var(--muted)]">Next.js + FastAPI</span>
            </div>
          </section>

          <section
            className="mt-24 border-t border-[var(--line)] pt-10 sm:mt-32"
            aria-labelledby="foundation-title"
          >
            <div className="grid gap-10 lg:grid-cols-[0.75fr_2fr]">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-[var(--muted)]">
                  Platform foundation
                </p>
                <h2
                  id="foundation-title"
                  className="mt-3 max-w-xs text-2xl font-semibold tracking-tight"
                >
                  A deliberate starting point
                </h2>
              </div>

              <div className="grid gap-4 sm:grid-cols-3">
                {foundationItems.map((item, index) => (
                  <article
                    key={item.title}
                    className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-5 shadow-[0_18px_50px_-35px_var(--shadow)] backdrop-blur"
                  >
                    <div className="flex items-center justify-between gap-4">
                      <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[var(--accent-strong)]">
                        {item.eyebrow}
                      </p>
                      <span
                        className="font-mono text-xs text-[var(--muted)]"
                        aria-hidden="true"
                      >
                        0{index + 1}
                      </span>
                    </div>
                    <h3 className="mt-8 text-base font-semibold leading-6">
                      {item.title}
                    </h3>
                    <p className="mt-3 text-sm leading-6 text-[var(--muted)]">
                      {item.description}
                    </p>
                  </article>
                ))}
              </div>
            </div>
          </section>
        </main>

        <footer className="relative mx-auto flex w-full max-w-6xl flex-col gap-2 border-t border-[var(--line)] px-6 py-6 text-xs text-[var(--muted)] sm:flex-row sm:items-center sm:justify-between sm:px-8 lg:px-10">
          <p>EvidenceGraph</p>
          <p>Foundation for verifiable research</p>
        </footer>
      </div>
    </>
  );
}
