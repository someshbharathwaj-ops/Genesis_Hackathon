"use client";

import React from "react";
import {
  BookOpen,
  CheckCircle2,
  FileCode,
  GraduationCap,
  Lightbulb,
  Sparkles,
} from "lucide-react";

interface StructuredExplanationProps {
  content: string;
}

interface ParsedSection {
  title: string;
  type: "concept" | "rules" | "example" | "takeaway" | "general";
  lines: string[];
}

export function StructuredExplanation({ content }: StructuredExplanationProps) {
  if (!content || !content.trim()) {
    return <p className="text-sm text-ink-muted italic">No explanation content available.</p>;
  }

  // 1. Check if the model used Markdown header sections (### or ##)
  const hasHeaders = /###?\s+/i.test(content);

  const sections: ParsedSection[] = [];

  if (hasHeaders) {
    const rawSections = content.split(/(?=###?\s+)/);
    for (const raw of rawSections) {
      const trimmed = raw.trim();
      if (!trimmed) continue;

      const lines = trimmed.split("\n");
      const headerLine = lines[0].replace(/^###?\s+/, "").trim();
      const bodyLines = lines.slice(1).map((l) => l.trim()).filter(Boolean);

      const lower = headerLine.toLowerCase();
      let type: ParsedSection["type"] = "general";
      if (lower.includes("concept") || lower.includes("glance")) type = "concept";
      else if (lower.includes("rule") || lower.includes("breakdown") || lower.includes("step")) type = "rules";
      else if (lower.includes("example") || lower.includes("worked")) type = "example";
      else if (lower.includes("takeaway") || lower.includes("summary") || lower.includes("remember")) type = "takeaway";

      sections.push({
        title: headerLine,
        type,
        lines: bodyLines,
      });
    }
  } else {
    // 2. Smart fallback: parse unbroken paragraphs or numbered rules (e.g. 1. Reflexivity: ... 2. Augmentation: ...)
    const paragraphs = content.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean);

    // Check if text has numbered items inside like "1. Reflexivity: ... 2. Augmentation: ..."
    const numberedRuleMatch = content.match(/\b([1-9]\.\s+[A-Za-z]+[\s\S]*?)(?=\b[1-9]\.|\s*$)/g);

    if (numberedRuleMatch && numberedRuleMatch.length >= 2) {
      // Split preamble from rules
      const firstRuleIndex = content.search(/\b1\.\s+[A-Za-z]+/);
      const preamble = firstRuleIndex > 0 ? content.slice(0, firstRuleIndex).trim() : "";
      
      if (preamble) {
        sections.push({
          title: "Concept at a Glance",
          type: "concept",
          lines: [preamble],
        });
      }

      sections.push({
        title: "Key Rules & Step-by-Step Breakdown",
        type: "rules",
        lines: numberedRuleMatch.map((r) => r.trim()),
      });
    } else {
      // General paragraph layout
      paragraphs.forEach((p, idx) => {
        if (idx === 0) {
          sections.push({
            title: "Core Concept",
            type: "concept",
            lines: [p],
          });
        } else if (idx === paragraphs.length - 1 && paragraphs.length > 2) {
          sections.push({
            title: "Quick Takeaway",
            type: "takeaway",
            lines: [p],
          });
        } else {
          sections.push({
            title: `Explanation (Part ${idx + 1})`,
            type: "general",
            lines: [p],
          });
        }
      });
    }
  }

  // Helper to format inline code / bold / arrows in a text block
  const formatInlineText = (text: string) => {
    // Replace arrows -> with nice unicode arrow →
    const withArrows = text.replace(/->/g, " → ");

    // Split on bold **text** markers
    const parts = withArrows.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-black text-ink">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col gap-4 text-sm leading-relaxed">
      {sections.map((sec, idx) => {
        switch (sec.type) {
          case "concept":
            return (
              <div
                key={idx}
                className="p-4 bg-brand-cyan/10 border-2 border-brand-cyan/40 rounded-friendly-sm flex flex-col gap-2"
              >
                <div className="flex items-center gap-2 text-xs font-black text-brand-cyan uppercase tracking-wider">
                  <Sparkles className="w-4 h-4 text-brand-cyan shrink-0" />
                  <span>{sec.title}</span>
                </div>
                <div className="text-ink font-semibold text-sm leading-relaxed space-y-2">
                  {sec.lines.map((l, li) => (
                    <p key={li}>{formatInlineText(l)}</p>
                  ))}
                </div>
              </div>
            );

          case "rules":
            return (
              <div
                key={idx}
                className="p-4 bg-white border-2 border-ink rounded-friendly-sm flex flex-col gap-3 shadow-tactile-sm"
              >
                <div className="flex items-center gap-2 text-xs font-black text-ink uppercase tracking-wider pb-1 border-b border-ink/10">
                  <GraduationCap className="w-4 h-4 text-brand-yellow shrink-0" />
                  <span>{sec.title}</span>
                </div>
                <div className="flex flex-col gap-2.5">
                  {sec.lines.map((l, li) => {
                    // Check if line is a numbered/bullet item e.g. "1. Reflexivity: ..."
                    const match = l.match(/^([1-9]\.|\*|-)\s*([^:]+)?:\s*([\s\S]+)$/);
                    if (match) {
                      const [, num, term, desc] = match;
                      return (
                        <div
                          key={li}
                          className="p-3 bg-surface-warm/40 border border-ink/20 rounded-friendly-sm flex items-start gap-2.5"
                        >
                          <span className="tactile-tag bg-brand-yellow text-ink text-[10px] font-black shrink-0 mt-0.5">
                            {num.replace(".", "")}
                          </span>
                          <div>
                            {term && (
                              <span className="font-black text-ink mr-1.5">{term.trim()}:</span>
                            )}
                            <span className="text-ink font-medium">{formatInlineText(desc)}</span>
                          </div>
                        </div>
                      );
                    }
                    return (
                      <div
                        key={li}
                        className="p-2.5 bg-surface-warm/30 border border-ink/15 rounded-friendly-sm text-ink font-medium"
                      >
                        {formatInlineText(l)}
                      </div>
                    );
                  })}
                </div>
              </div>
            );

          case "example":
            return (
              <div
                key={idx}
                className="p-4 bg-brand-yellow/10 border-2 border-brand-yellow/50 rounded-friendly-sm flex flex-col gap-2"
              >
                <div className="flex items-center gap-2 text-xs font-black text-ink uppercase tracking-wider">
                  <Lightbulb className="w-4 h-4 text-brand-yellow shrink-0" />
                  <span>{sec.title}</span>
                </div>
                <div className="p-3 bg-white/90 border border-ink/20 rounded font-mono text-xs text-ink leading-relaxed space-y-1.5">
                  {sec.lines.map((l, li) => (
                    <p key={li}>{formatInlineText(l)}</p>
                  ))}
                </div>
              </div>
            );

          case "takeaway":
            return (
              <div
                key={idx}
                className="p-4 bg-brand-green/10 border-2 border-brand-green/40 rounded-friendly-sm flex items-start gap-3"
              >
                <CheckCircle2 className="w-5 h-5 text-brand-green shrink-0 mt-0.5" />
                <div className="flex flex-col gap-1">
                  <div className="text-xs font-black text-brand-green uppercase tracking-wider">
                    {sec.title}
                  </div>
                  <div className="text-xs font-bold text-ink leading-relaxed">
                    {sec.lines.map((l, li) => (
                      <span key={li}>{formatInlineText(l)} </span>
                    ))}
                  </div>
                </div>
              </div>
            );

          default:
            return (
              <div
                key={idx}
                className="p-3.5 bg-surface-warm/20 border border-ink/20 rounded-friendly-sm flex flex-col gap-1.5"
              >
                <div className="text-xs font-black text-ink-muted uppercase tracking-wider">
                  {sec.title}
                </div>
                <div className="text-ink font-medium space-y-1.5">
                  {sec.lines.map((l, li) => (
                    <p key={li}>{formatInlineText(l)}</p>
                  ))}
                </div>
              </div>
            );
        }
      })}
    </div>
  );
}
