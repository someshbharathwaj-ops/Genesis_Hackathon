"use client";

import React from "react";
import {
  CheckCircle2,
  GraduationCap,
  Lightbulb,
  Sparkles,
} from "lucide-react";

interface StructuredExplanationProps {
  content: string;
}

interface StructuredPoint {
  prefix?: string;
  body: string;
}

interface ParsedSection {
  title: string;
  type: "concept" | "rules" | "example" | "takeaway" | "general";
  points: StructuredPoint[];
}

/**
 * Clean and normalize text:
 * - Strips echoed prompt fragments (OFFICIAL COURSE EXCERPTS, Copyright, etc.)
 * - Replaces ascii arrows with clean unicode arrows
 * - De-duplicates redundant sentences
 */
function sanitizeRawText(raw: string): string {
  // 1. Cut off prompt echoes or lecture dumps
  let cleaned = raw;
  const cutOffPatterns = [
    /\bOFFICIAL COURSE EXCERPTS\b[\s\S]*/i,
    /\b--- EXCERPT\b[\s\S]*/i,
    /\bCopyright\s+©[\s\S]*/i,
    /\bSlide\s+\d+-\s*\d+[\s\S]*/i,
  ];
  for (const pat of cutOffPatterns) {
    cleaned = cleaned.replace(pat, "");
  }

  // 2. Unicode arrows
  cleaned = cleaned.replace(/->/g, " → ").replace(/-->/g, " → ");

  return cleaned.trim();
}

/**
 * Break a block of text into distinct, crisp bullet points.
 * Ensures no bullet point exceeds 2 sentences.
 */
function extractBulletPoints(textBlock: string): StructuredPoint[] {
  const points: StructuredPoint[] = [];

  // Split on newlines or explicit bullet/numbered markers
  const rawLines = textBlock.split(/\n+/).map((l) => l.trim()).filter(Boolean);

  for (const line of rawLines) {
    // Check if line starts with bullet marker or number (e.g. "1. Reflexivity: ...", "• Rule 1: ...", "- Item")
    const markerMatch = line.match(/^([1-9]\.|\*|•|-)\s*(?:(?:\*\*)?([^:]+?)(?:\*\*)?)?:\s*([\s\S]+)$/);
    if (markerMatch) {
      const [, , rawPrefix, rawBody] = markerMatch;
      const cleanPrefix = rawPrefix ? rawPrefix.replace(/\*\*/g, "").trim() : undefined;
      
      // If the body is too long (contains multiple sentences), split it into sub-points
      const sentences = splitIntoSentences(rawBody);
      if (sentences.length > 2) {
        // Take the main definition as first point
        points.push({
          prefix: cleanPrefix,
          body: sentences[0],
        });
        // Remaining significant sentences become concise follow-up bullets
        for (let i = 1; i < Math.min(sentences.length, 3); i++) {
          if (!isFillerSentence(sentences[i])) {
            points.push({
              body: sentences[i],
            });
          }
        }
      } else {
        points.push({
          prefix: cleanPrefix,
          body: rawBody,
        });
      }
      continue;
    }

    // Check if standard bullet item without colon (e.g. "• Given: A → B")
    const simpleBulletMatch = line.match(/^([1-9]\.|\*|•|-)\s*([\s\S]+)$/);
    if (simpleBulletMatch) {
      points.push({
        body: simpleBulletMatch[2].trim(),
      });
      continue;
    }

    // Long unbroken narrative sentences: split into clean bullet points
    const sentences = splitIntoSentences(line);
    for (const s of sentences) {
      if (!isFillerSentence(s)) {
        points.push({
          body: s,
        });
      }
    }
  }

  // De-duplicate points that repeat the same concept
  const uniquePoints: StructuredPoint[] = [];
  const seenBodies = new Set<string>();

  for (const p of points) {
    const norm = p.body.toLowerCase().replace(/[^a-z0-9]/g, "").slice(0, 35);
    if (!seenBodies.has(norm)) {
      seenBodies.add(norm);
      uniquePoints.push(p);
    }
  }

  return uniquePoints.slice(0, 6); // Max 6 crisp bullets per section
}

function splitIntoSentences(text: string): string[] {
  return text
    .split(/(?<=[.?!])\s+(?=[A-Z0-9])/)
    .map((s) => s.trim())
    .filter((s) => s.length > 10);
}

function isFillerSentence(sentence: string): boolean {
  const lower = sentence.toLowerCase();
  return (
    lower.includes("the provided excerpts do not contain") ||
    lower.includes("since the excerpts do not provide explicit") ||
    lower.includes("i cannot directly cite the source") ||
    lower.includes("in accordance with recall's grounding policy") ||
    lower.includes("as mentioned in the provided excerpts")
  );
}

export function StructuredExplanation({ content }: StructuredExplanationProps) {
  const sanitized = sanitizeRawText(content);
  if (!sanitized) {
    return <p className="text-xs text-ink-muted italic">No explanation content available.</p>;
  }

  const sections: ParsedSection[] = [];
  const hasMarkdownHeaders = /###?\s+/i.test(sanitized);

  if (hasMarkdownHeaders) {
    const rawChunks = sanitized.split(/(?=###?\s+)/);
    for (const chunk of rawChunks) {
      const trimmed = chunk.trim();
      if (!trimmed) continue;

      const lines = trimmed.split("\n");
      const title = lines[0].replace(/^###?\s+/, "").trim();
      const body = lines.slice(1).join("\n").trim();

      const lower = title.toLowerCase();
      let type: ParsedSection["type"] = "general";
      if (lower.includes("concept") || lower.includes("glance")) type = "concept";
      else if (lower.includes("rule") || lower.includes("breakdown") || lower.includes("step")) type = "rules";
      else if (lower.includes("example") || lower.includes("worked")) type = "example";
      else if (lower.includes("takeaway") || lower.includes("summary")) type = "takeaway";

      const points = extractBulletPoints(body || title);
      if (points.length > 0) {
        sections.push({ title, type, points });
      }
    }
  } else {
    // Unstructured text fallback: synthesize clean structured sections
    const allPoints = extractBulletPoints(sanitized);
    if (allPoints.length <= 2) {
      sections.push({
        title: "Concept Summary",
        type: "concept",
        points: allPoints,
      });
    } else {
      sections.push({
        title: "Concept at a Glance",
        type: "concept",
        points: allPoints.slice(0, 2),
      });
      sections.push({
        title: "Key Breakdown & Rules",
        type: "rules",
        points: allPoints.slice(2, -1),
      });
      sections.push({
        title: "Quick Takeaway",
        type: "takeaway",
        points: allPoints.slice(-1),
      });
    }
  }

  const formatInlineText = (text: string) => {
    // Format inline formulas / codes like X → Y or A → B
    const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\b[A-Za-z]+(?:\s*[→]\s*[A-Za-z]+)+\b)/g);
    return parts.map((part, i) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={i} className="font-black text-ink">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.includes("→")) {
        return (
          <span
            key={i}
            className="inline-block px-1.5 py-0.5 bg-brand-cyan/15 text-ink font-mono font-bold text-xs rounded border border-brand-cyan/30 mx-0.5"
          >
            {part.trim()}
          </span>
        );
      }
      return part;
    });
  };

  return (
    <div className="flex flex-col gap-3.5 text-xs leading-relaxed">
      {sections.map((sec, sIdx) => {
        switch (sec.type) {
          case "concept":
            return (
              <div
                key={sIdx}
                className="p-3.5 bg-brand-cyan/10 border-2 border-brand-cyan/50 rounded-friendly-sm flex flex-col gap-2"
              >
                <div className="flex items-center gap-1.5 text-[11px] font-black text-brand-cyan uppercase tracking-wider">
                  <Sparkles className="w-3.5 h-3.5 text-brand-cyan shrink-0" />
                  <span>{sec.title}</span>
                </div>
                <ul className="flex flex-col gap-1.5 pl-1">
                  {sec.points.map((pt, pIdx) => (
                    <li key={pIdx} className="flex items-start gap-2 text-ink font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-cyan mt-1.5 shrink-0" />
                      <div>
                        {pt.prefix && <strong className="font-black text-ink mr-1">{pt.prefix}:</strong>}
                        <span>{formatInlineText(pt.body)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            );

          case "rules":
            return (
              <div
                key={sIdx}
                className="p-4 bg-white border-2 border-ink rounded-friendly-sm flex flex-col gap-2.5 shadow-tactile-sm"
              >
                <div className="flex items-center gap-1.5 text-[11px] font-black text-ink uppercase tracking-wider pb-1.5 border-b border-ink/10">
                  <GraduationCap className="w-4 h-4 text-brand-yellow shrink-0" />
                  <span>{sec.title}</span>
                </div>
                <div className="grid grid-cols-1 gap-2">
                  {sec.points.map((pt, pIdx) => (
                    <div
                      key={pIdx}
                      className="p-2.5 bg-surface-warm/40 border border-ink/20 rounded flex items-start gap-2.5"
                    >
                      <span className="tactile-tag bg-brand-yellow text-ink text-[10px] font-black shrink-0 mt-0.5 py-0 px-1.5">
                        {pIdx + 1}
                      </span>
                      <div className="text-ink font-medium leading-relaxed">
                        {pt.prefix && <strong className="font-black text-ink mr-1">{pt.prefix}:</strong>}
                        <span>{formatInlineText(pt.body)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );

          case "example":
            return (
              <div
                key={sIdx}
                className="p-3.5 bg-brand-yellow/10 border-2 border-brand-yellow/60 rounded-friendly-sm flex flex-col gap-2"
              >
                <div className="flex items-center gap-1.5 text-[11px] font-black text-ink uppercase tracking-wider">
                  <Lightbulb className="w-3.5 h-3.5 text-brand-yellow shrink-0" />
                  <span>{sec.title}</span>
                </div>
                <ul className="flex flex-col gap-1.5 pl-1">
                  {sec.points.map((pt, pIdx) => (
                    <li key={pIdx} className="flex items-start gap-2 text-ink font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-brand-yellow mt-1.5 shrink-0" />
                      <div>
                        {pt.prefix && <strong className="font-black text-ink mr-1">{pt.prefix}:</strong>}
                        <span>{formatInlineText(pt.body)}</span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            );

          case "takeaway":
            return (
              <div
                key={sIdx}
                className="p-3 bg-brand-green/10 border-2 border-brand-green/50 rounded-friendly-sm flex items-start gap-2.5"
              >
                <CheckCircle2 className="w-4 h-4 text-brand-green shrink-0 mt-0.5" />
                <div className="flex flex-col gap-0.5">
                  <span className="text-[10px] font-black text-brand-green uppercase tracking-wider">
                    {sec.title}
                  </span>
                  <div className="text-ink font-bold text-xs leading-relaxed">
                    {sec.points.map((pt, pIdx) => (
                      <span key={pIdx}>{formatInlineText(pt.body)} </span>
                    ))}
                  </div>
                </div>
              </div>
            );

          default:
            return (
              <div
                key={sIdx}
                className="p-3 bg-surface-warm/25 border border-ink/20 rounded-friendly-sm flex flex-col gap-1.5"
              >
                <span className="text-[10px] font-black text-ink-muted uppercase tracking-wider">
                  {sec.title}
                </span>
                <ul className="flex flex-col gap-1 pl-1">
                  {sec.points.map((pt, pIdx) => (
                    <li key={pIdx} className="flex items-start gap-2 text-ink font-medium">
                      <span className="w-1.5 h-1.5 rounded-full bg-ink-muted mt-1.5 shrink-0" />
                      <span>{formatInlineText(pt.body)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            );
        }
      })}
    </div>
  );
}
