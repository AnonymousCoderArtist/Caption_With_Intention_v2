/** Cinematic welcome screen — brand hero + live color-sync specimen. */
import { useEffect, useRef } from "react";
import { gsap } from "gsap";
import { Icon } from "@/lib/icons";
import { MAIN_COLORS } from "@/lib/theme";

/* animated specimen: words color-sync + pop in sequence, on loop */
function Specimen() {
  const root = useRef<HTMLDivElement>(null);
  const refs = useRef<(HTMLSpanElement | null)[]>([]);

  const words = [
    { t: "Every", c: "#E5E517" },
    { t: "caption", c: "#17E5E5" },
    { t: "carries", c: "#E51717" },
    { t: "who,", c: "#E58017" },
    { t: "when,", c: "#17E517" },
    { t: "and", c: "#E517E5" },
    { t: "how.", c: "#E5E517" },
  ];

  useEffect(() => {
    const beat = 0.55;
    const hold = 0.9;
    const tl = gsap.timeline({ repeat: -1, repeatDelay: 0.5, delay: 0.6 });
    words.forEach((wd, i) => {
      const el = refs.current[i];
      if (!el) return;
      const at = i * beat;
      // smooth color + glow ease-in (no hard cut)
      tl.to(
        el,
        { color: wd.c, textShadow: `0 0 18px ${wd.c}88`, duration: 0.22, ease: "power2.out" },
        at,
      );
      // asymmetric pop: quick ease-out attack, gentle ease-in-out settle
      tl.fromTo(
        el,
        { scale: 1 },
        { scale: 1.16, duration: 0.13, ease: "power3.out" },
        at,
      );
      tl.to(el, { scale: 1, duration: 0.3, ease: "power2.inOut" }, at + 0.13);
    });
    const resetAt = words.length * beat + hold;
    tl.to(
      refs.current.filter(Boolean),
      {
        color: "#ffffff",
        textShadow: "0 0 0 rgba(0,0,0,0)",
        opacity: 0.9,
        duration: 0.5,
        ease: "power1.out",
      },
      resetAt,
    );
    return () => {
      tl.kill();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      ref={root}
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "center",
        gap: "0.22em",
        font: "500 clamp(22px, 3.4vw, 40px)/1.25 var(--font-sans)",
        letterSpacing: "-0.02em",
      }}
    >
      {words.map((wd, i) => (
        <span
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          style={{
            display: "inline-block",
            color: "rgba(255,255,255,0.9)",
            willChange: "transform, color",
            textShadow: "0 0 0 rgba(0,0,0,0)",
          }}
        >
          {wd.t}
        </span>
      ))}
    </div>
  );
}

/* drifting ambient background */
function Ambient() {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const ctx = gsap.context(() => {
      gsap.to(".amb-a", { x: 80, y: -40, duration: 14, yoyo: true, repeat: -1, ease: "sine.inOut" });
      gsap.to(".amb-b", { x: -60, y: 50, duration: 18, yoyo: true, repeat: -1, ease: "sine.inOut" });
      gsap.to(".amb-c", { x: 40, y: 60, duration: 22, yoyo: true, repeat: -1, ease: "sine.inOut" });
      gsap.to(".grain", { opacity: 0.05, duration: 1.2, yoyo: true, repeat: -1, ease: "sine.inOut" });
    }, root);
    return () => ctx.revert();
  }, []);

  const orb = (cls: string, size: number, x: string, y: string, c: string, o: number) => (
    <div
      className={cls}
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: size,
        height: size,
        borderRadius: "50%",
        background: c,
        filter: "blur(90px)",
        opacity: o,
        mixBlendMode: "screen",
        pointerEvents: "none",
      }}
    />
  );

  return (
    <div ref={root} style={{ position: "absolute", inset: 0, overflow: "hidden" }}>
      {orb("amb-a", 520, "8%", "4%", "rgba(229,229,23,0.55)", 0.4)}
      {orb("amb-b", 560, "62%", "8%", "rgba(23,229,229,0.5)", 0.35)}
      {orb("amb-c", 520, "52%", "60%", "rgba(229,23,229,0.4)", 0.3)}
      <div
        className="grain"
        style={{
          position: "absolute",
          inset: "-50%",
          opacity: 0.04,
          mixBlendMode: "overlay",
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(120% 90% at 50% 30%, transparent 40%, rgba(0,0,0,0.6) 100%)",
        }}
      />
    </div>
  );
}

export function WelcomeScreen({
  onNew,
  onOpen,
}: {
  onNew: () => void;
  onOpen: () => void;
}) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ctx = gsap.context(() => {
      const items = gsap.utils.toArray<HTMLElement>("[data-rise]");
      gsap.fromTo(
        items,
        { y: 26, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 1,
          ease: "power3.out",
          stagger: 0.09,
          delay: 0.15,
        },
      );
      gsap.fromTo(
        "[data-mark]",
        { scale: 0.8, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.9, ease: "back.out(1.6)", delay: 0.05 },
      );
    }, root);
    return () => ctx.revert();
  }, []);

  return (
    <div
      ref={root}
      style={{
        position: "relative",
        width: "100vw",
        height: "100vh",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--bg-0)",
      }}
    >
      <Ambient />

      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: "var(--sp-5)",
          padding: "0 24px",
          maxWidth: 760,
          textAlign: "center",
        }}
      >
        {/* brand mark */}
        <div
          data-mark
          style={{
            display: "flex",
            alignItems: "center",
            gap: "14px",
            opacity: 0,
          }}
        >
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 16,
              display: "grid",
              placeItems: "center",
              background:
                "linear-gradient(145deg, rgba(229,229,23,0.24), rgba(229,229,23,0.03))",
              border: "1px solid var(--accent-soft)",
              boxShadow: "var(--glow-soft), inset 0 1px 0 rgba(255,255,255,0.16)",
            }}
          >
            <Icon name="logo" size={30} strokeWidth={1.7} style={{ color: "var(--accent)" }} />
          </div>
          <div style={{ textAlign: "left" }}>
            <div
              className="type-brand"
              style={{
                fontSize: 22,
                color: "var(--text-100)",
                letterSpacing: "0.16em",
              }}
            >
              <b style={{ color: "var(--accent-text)" }}>CWI</b>
            </div>
            <div style={{ fontSize: 10.5, letterSpacing: "0.32em", color: "var(--text-400)", textTransform: "uppercase" }}>
              Editor
            </div>
          </div>
        </div>

        {/* title */}
        <div data-rise style={{ opacity: 0 }}>
          <h1
            className="type-display"
            style={{
              fontSize: "clamp(34px, 6vw, 64px)",
              fontWeight: 300,
              letterSpacing: "-0.03em",
              color: "var(--text-100)",
              lineHeight: 1.05,
            }}
          >
            Caption
            <span style={{ color: "var(--text-400)", fontWeight: 200 }}> With </span>
            Intention
          </h1>
        </div>

        {/* specimen */}
        <div data-rise style={{ opacity: 0, margin: "4px 0" }}>
          <Specimen />
        </div>

        {/* subtitle */}
        <div data-rise style={{ opacity: 0, maxWidth: 460 }}>
          <p
            style={{
              fontSize: 14.5,
              color: "var(--text-300)",
              lineHeight: 1.7,
              fontWeight: 420,
            }}
          >
            A cinematic accessibility editor. Color, word-onset sync, and
            intonation-driven type — every decision editable, every rule
            deterministic.
          </p>
        </div>

        {/* CTAs */}
        <div
          data-rise
          style={{
            opacity: 0,
            display: "flex",
            gap: "var(--sp-3)",
            marginTop: "6px",
            flexWrap: "wrap",
            justifyContent: "center",
          }}
        >
          <button
            className="primary"
            onClick={onNew}
            style={{ padding: "14px 26px", fontSize: 14, borderRadius: "var(--r-lg)" }}
          >
            <Icon name="plus" size={16} strokeWidth={2.2} />
            New Project
          </button>
          <button
            className="ghost"
            onClick={onOpen}
            style={{
              padding: "14px 24px",
              fontSize: 14,
              borderRadius: "var(--r-lg)",
              border: "1px solid var(--border-2)",
            }}
          >
            <Icon name="monitor" size={16} />
            Open Editor
          </button>
        </div>
      </div>

      {/* footer: version + palette + mission */}
      <div
        data-rise
        style={{
          opacity: 0,
          position: "absolute",
          bottom: 30,
          left: 0,
          right: 0,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 14,
          zIndex: 2,
        }}
      >
        <div style={{ display: "flex", gap: 7 }}>
          {MAIN_COLORS.map((c) => (
            <span
              key={c.hex}
              title={c.name}
              style={{
                width: 10,
                height: 10,
                borderRadius: "50%",
                background: c.hex,
                boxShadow: `0 0 8px ${c.hex}66`,
              }}
            />
          ))}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-400)", letterSpacing: "0.14em", textTransform: "uppercase" }}>
          v2.0 · Open Source · Made for the Deaf &amp; hard-of-hearing
        </div>
      </div>
    </div>
  );
}
