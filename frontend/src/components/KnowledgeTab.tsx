"use client";

import React, { useEffect, useState } from "react";
import {
  BookOpen,
  CheckCircle2,
  FileText,
  FileUp,
  Layers,
  Search,
  Trash2,
} from "lucide-react";
import {
  CourseDocumentDetailResponse,
  CourseDocumentResponse,
  CourseResponse,
  RetrievalResponse,
} from "../types";
import { recallApi } from "../lib/api-client";

interface KnowledgeTabProps {
  course: CourseResponse | null;
}

export function KnowledgeTab({ course }: KnowledgeTabProps) {
  const [documents, setDocuments] = useState<CourseDocumentResponse[]>([]);
  const [loadingDocs, setLoadingDocs] = useState<boolean>(true);
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Selected Doc Details
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [docDetail, setDocDetail] = useState<CourseDocumentDetailResponse | null>(null);
  const [loadingDetail, setLoadingDetail] = useState<boolean>(false);

  // Semantic Vector Retrieval Sandbox
  const [searchQuery, setSearchQuery] = useState<string>("Armstrong axioms transitivity");
  const [retrievalResults, setRetrievalResults] = useState<RetrievalResponse | null>(null);
  const [isSearching, setIsSearching] = useState<boolean>(false);

  const fetchDocuments = async () => {
    if (!course) return;
    setLoadingDocs(true);
    try {
      const docs = await recallApi.listCourseDocuments(course.id);
      setDocuments(docs);
      if (docs.length > 0 && !selectedDocId) {
        handleViewDocDetail(docs[0].id);
      }
    } catch {
      setDocuments([]);
    } finally {
      setLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [course?.id]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !course) return;

    setIsUploading(true);
    setUploadError(null);
    try {
      await recallApi.uploadDocument(course.id, file);
      await fetchDocuments();
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Document upload failed");
    } finally {
      setIsUploading(false);
      e.target.value = "";
    }
  };

  const handleViewDocDetail = async (docId: string) => {
    if (!course) return;
    setSelectedDocId(docId);
    setLoadingDetail(true);
    try {
      const detail = await recallApi.getDocumentDetail(course.id, docId);
      setDocDetail(detail);
    } catch {
      setDocDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!course || !confirm("Are you sure you want to delete this course document and its indexed chunks?"))
      return;
    try {
      await recallApi.deleteDocument(course.id, docId);
      if (selectedDocId === docId) {
        setSelectedDocId(null);
        setDocDetail(null);
      }
      await fetchDocuments();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete document.");
    }
  };

  const handleSearchRetrieval = async () => {
    if (!course || !searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const res = await recallApi.retrieveKnowledge(course.id, searchQuery, 3);
      setRetrievalResults(res);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Retrieval query failed.");
    } finally {
      setIsSearching(false);
    }
  };

  if (!course) {
    return (
      <div className="tactile-card p-8 text-center text-ink-muted">
        <BookOpen className="w-8 h-8 mx-auto mb-2 text-ink-faint" />
        <p className="font-bold">Select a course to view ingested documents and knowledge grounding.</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-8">
      {/* Upload & Material Status Header */}
      <section className="tactile-card p-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="tactile-tag bg-brand-cyan text-ink">KNOWLEDGE ENGINE</span>
            <span className="text-xs font-bold text-ink-muted">Tenant-Isolated RAG Layer</span>
          </div>
          <h2 className="text-2xl font-black text-ink">Course Learning Materials</h2>
          <p className="text-sm text-ink-muted mt-1 max-w-2xl font-medium">
            Ingest authoritative course lecture slides and reading materials (.PDF / .TXT) with repeat-safe
            content hashing and slide-level chunk metadata.
          </p>
        </div>

        {/* Upload Button */}
        <div>
          <label className={`tactile-btn-yellow text-xs py-2 px-4 cursor-pointer ${isUploading ? "opacity-50" : ""}`}>
            <FileUp className={`w-4 h-4 ${isUploading ? "animate-bounce" : ""}`} />
            <span>{isUploading ? "Ingesting & Chunking..." : "Upload Material (PDF/TXT)"}</span>
            <input
              type="file"
              accept=".pdf,.txt"
              onChange={handleFileUpload}
              disabled={isUploading}
              className="hidden"
            />
          </label>
          {uploadError && (
            <div className="text-xs text-brand-coral font-bold mt-2 max-w-xs">{uploadError}</div>
          )}
        </div>
      </section>

      {/* Main Grid: Documents List & Chunks Inspector */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Ingested Documents List */}
        <div className="lg:col-span-5 flex flex-col gap-4">
          <h3 className="text-lg font-black text-ink flex items-center gap-2">
            <FileText className="w-5 h-5 text-brand-cyan" />
            <span>Ingested Documents ({documents.length})</span>
          </h3>

          {loadingDocs ? (
            <div className="tactile-card p-6 text-center text-xs font-bold text-ink-muted">
              Loading course documents...
            </div>
          ) : documents.length === 0 ? (
            <div className="tactile-card p-8 text-center text-ink-muted text-xs font-medium">
              No documents ingested yet for {course.code}. Upload lecture slides or notes above.
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {documents.map((doc) => {
                const isSelected = selectedDocId === doc.id;
                return (
                  <div
                    key={doc.id}
                    onClick={() => handleViewDocDetail(doc.id)}
                    className={`tactile-card p-4 cursor-pointer transition-all ${
                      isSelected ? "border-brand-yellow shadow-hard-lg" : "hover:bg-surface-warm/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <FileText className="w-4 h-4 text-brand-cyan" />
                        <span className="font-bold text-sm text-ink truncate max-w-[200px]">
                          {doc.filename}
                        </span>
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="tactile-tag bg-brand-green text-ink text-[9px] py-0 px-1.5 uppercase">
                          {doc.status}
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDeleteDocument(doc.id);
                          }}
                          className="text-ink-faint hover:text-brand-coral p-1"
                          title="Delete document"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="mt-3 text-[11px] text-ink-muted font-medium flex items-center justify-between border-t border-ink/10 pt-2">
                      <span>Pages: {doc.page_count}</span>
                      <span>{(doc.file_size_bytes / 1024).toFixed(1)} KB</span>
                      <span className="font-mono text-[9px] truncate max-w-[90px]" title={doc.content_hash}>
                        {doc.content_hash.substring(0, 8)}...
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Chunks Inspector & Semantic Search Sandbox */}
        <div className="lg:col-span-7 flex flex-col gap-6">
          {/* Semantic Search Sandbox */}
          <div className="tactile-card p-5 flex flex-col gap-3">
            <h4 className="text-sm font-black text-ink flex items-center gap-2">
              <Search className="w-4 h-4 text-brand-yellow" />
              <span>Vector Knowledge Retrieval Sandbox</span>
            </h4>
            <p className="text-xs text-ink-muted font-medium">
              Test tenant-isolated vector retrieval directly against course chunks to observe citation grounding.
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Ask or query curriculum concept..."
                className="tactile-input text-xs flex-1"
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleSearchRetrieval();
                }}
              />
              <button
                onClick={handleSearchRetrieval}
                disabled={isSearching}
                className="tactile-btn-yellow text-xs py-2 px-4"
              >
                <Search className={`w-3.5 h-3.5 ${isSearching ? "animate-spin" : ""}`} />
                <span>Search</span>
              </button>
            </div>

            {retrievalResults && (
              <div className="mt-2 flex flex-col gap-2 pt-3 border-t border-ink/10">
                <div className="text-xs font-bold text-ink flex items-center justify-between">
                  <span>{retrievalResults.matches_count} Verified Matches Found:</span>
                  <span className="text-[10px] text-ink-muted">Strict Threshold: 0.30</span>
                </div>

                {retrievalResults.matches.length === 0 ? (
                  <div className="p-4 bg-brand-coral/10 border-2 border-brand-coral rounded-friendly-sm text-xs font-bold text-brand-coral">
                    No relevant chunks met confidence threshold. System will explicitly ABSTAIN rather than hallucinate.
                  </div>
                ) : (
                  retrievalResults.matches.map((m) => (
                    <div
                      key={m.chunk_id}
                      className="p-3 bg-surface-warm/40 border-2 border-ink rounded-friendly-sm text-xs flex flex-col gap-1.5"
                    >
                      <div className="flex items-center justify-between text-[11px]">
                        <span className="font-bold text-brand-cyan">
                          [Lecture: {m.filename}, Page {m.page_number}]
                        </span>
                        <span className="tactile-tag bg-brand-green text-ink text-[9px] py-0 px-1">
                          Score: {(m.similarity_score * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="text-ink-muted font-medium italic">&quot;{m.content}&quot;</p>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Selected Document Chunks Inspector */}
          {docDetail && (
            <div className="tactile-card p-5 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <h4 className="text-sm font-black text-ink flex items-center gap-2">
                  <Layers className="w-4 h-4 text-brand-cyan" />
                  <span>Extracted Semantic Chunks ({docDetail.chunks.length})</span>
                </h4>
                <span className="text-xs text-ink-muted font-bold">{docDetail.document.filename}</span>
              </div>

              <div className="flex flex-col gap-3 max-h-[360px] overflow-y-auto pr-1">
                {docDetail.chunks.map((chunk) => (
                  <div
                    key={chunk.id}
                    className="p-3 bg-white border border-ink rounded-friendly-sm text-xs flex flex-col gap-1"
                  >
                    <div className="flex items-center justify-between text-[10px] text-ink-muted font-mono">
                      <span>Chunk #{chunk.chunk_index} • Page {chunk.page_number}</span>
                      <span>{chunk.token_count} Tokens</span>
                    </div>
                    <p className="text-ink font-medium leading-relaxed">{chunk.content}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
