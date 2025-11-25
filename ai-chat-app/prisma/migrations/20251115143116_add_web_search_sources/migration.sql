-- AlterTable
ALTER TABLE "messages" ADD COLUMN     "citations" JSONB,
ADD COLUMN     "is_web_search" BOOLEAN NOT NULL DEFAULT false;
