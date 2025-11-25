-- CreateExtension
CREATE EXTENSION IF NOT EXISTS "vector";

-- AlterTable
ALTER TABLE "pdfs" ADD COLUMN     "errorMessage" TEXT,
ADD COLUMN     "processedAt" TIMESTAMP(3),
ADD COLUMN     "status" TEXT NOT NULL DEFAULT 'processing',
ADD COLUMN     "totalChunks" INTEGER NOT NULL DEFAULT 0,
ADD COLUMN     "totalPages" INTEGER;

-- CreateTable
CREATE TABLE "document_chunks" (
    "id" TEXT NOT NULL,
    "pdf_id" TEXT NOT NULL,
    "chunk_index" INTEGER NOT NULL,
    "content" TEXT NOT NULL,
    "embedding" vector,
    "page_number" INTEGER,
    "start_char" INTEGER,
    "end_char" INTEGER,
    "token_count" INTEGER,
    "metadata" JSONB,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "document_chunks_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "document_chunks_pdf_id_idx" ON "document_chunks"("pdf_id");

-- CreateIndex
CREATE INDEX "document_chunks_chunk_index_idx" ON "document_chunks"("chunk_index");

-- CreateIndex
CREATE INDEX "pdfs_status_idx" ON "pdfs"("status");

-- AddForeignKey
ALTER TABLE "document_chunks" ADD CONSTRAINT "document_chunks_pdf_id_fkey" FOREIGN KEY ("pdf_id") REFERENCES "pdfs"("id") ON DELETE CASCADE ON UPDATE CASCADE;
