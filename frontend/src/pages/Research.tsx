import { FormEvent, useMemo, useState } from 'react';
import { AlertCircle, BookOpen, ExternalLink, FileSearch, Loader2, Send } from 'lucide-react';

import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import { usePortfolioConfig } from '@/hooks/use-portfolio';
import { askResearch, ResearchCitation, ResearchResponse } from '@/lib/api';
import { supportedPortfolioTickers } from '@/lib/research';

const NOT_FOUND = 'Not found in the filings.';

export function ResearchAnswer({
  answer,
  citations,
}: {
  answer: string;
  citations: ResearchCitation[];
}) {
  const citationMap = new Map(citations.map((citation) => [citation.citation, citation]));
  const parts = answer.split(/(\[\d+])/g);
  return (
    <div className="space-y-5">
      <div className={answer === NOT_FOUND ? 'text-muted-foreground italic' : 'text-foreground leading-7'}>
        {parts.map((part, index) => {
          const match = part.match(/^\[(\d+)]$/);
          if (!match) return <span key={`${part}-${index}`}>{part}</span>;
          const citation = citationMap.get(Number(match[1]));
          if (!citation) return <span key={`${part}-${index}`}>{part}</span>;
          return (
            <a
              key={`${part}-${index}`}
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              aria-label={`Open citation ${citation.citation} on SEC.gov`}
              className="mx-0.5 font-mono text-sm font-semibold text-primary hover:underline"
            >
              {part}
            </a>
          );
        })}
      </div>

      {citations.length > 0 && (
        <div className="space-y-2 border-t border-border pt-4">
          <h3 className="font-display text-sm font-semibold text-foreground">SEC sources</h3>
          {citations.map((citation) => (
            <a
              key={citation.chunk_id}
              href={citation.url}
              target="_blank"
              rel="noreferrer"
              className="group flex items-start justify-between gap-4 rounded-lg border border-border bg-background/40 p-3 transition-colors hover:border-primary/40"
            >
              <div className="min-w-0">
                <div className="font-mono text-xs font-semibold text-primary">
                  [{citation.citation}] {citation.ticker} · {citation.form} · {citation.filing_date}
                </div>
                <div className="mt-1 text-sm text-foreground">{citation.section}</div>
                <p className="mt-1 line-clamp-2 text-xs leading-5 text-muted-foreground">
                  {citation.excerpt}
                </p>
              </div>
              <ExternalLink size={15} className="mt-0.5 flex-shrink-0 text-muted-foreground group-hover:text-primary" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

const Research = () => {
  const portfolio = usePortfolioConfig();
  const portfolioTickers = useMemo(
    () => supportedPortfolioTickers(portfolio?.holdings ?? []),
    [portfolio],
  );
  const [selected, setSelected] = useState<string[]>(portfolioTickers);
  const [question, setQuestion] = useState('');
  const [result, setResult] = useState<ResearchResponse | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const toggleTicker = (ticker: string) => {
    setSelected((current) => current.includes(ticker)
      ? current.filter((value) => value !== ticker)
      : [...current, ticker]);
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    const clean = question.trim();
    if (!clean || selected.length === 0 || loading) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      setResult(await askResearch(clean, selected));
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Research request failed';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <AppLayout title="Research">
      <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
        <BackButton to="/dashboard" label="Back to Dashboard" />

        <div className="mb-6 flex items-start gap-3">
          <div className="rounded-xl border border-primary/20 bg-primary/10 p-2.5">
            <BookOpen className="text-primary" size={22} />
          </div>
          <div>
            <h1 className="font-display text-2xl font-bold text-foreground">Arcus Research</h1>
            <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
              Ask about companies you hold. Answers use only their latest 10-K and two latest
              earnings releases, with links to the original SEC filings.
            </p>
          </div>
        </div>

        {portfolioTickers.length === 0 ? (
          <Card className="p-8 text-center">
            <FileSearch className="mx-auto mb-3 text-muted-foreground" size={30} />
            <h2 className="font-display font-semibold text-foreground">No indexed holdings found</h2>
            <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
              Add at least one supported US stock to your portfolio and run an analysis first.
            </p>
          </Card>
        ) : (
          <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_300px]">
            <div className="space-y-5">
              <Card className="p-5">
                <form onSubmit={submit} className="space-y-4">
                  <div>
                    <label htmlFor="research-question" className="font-display text-sm font-semibold text-foreground">
                      Ask a filing question
                    </label>
                    <Textarea
                      id="research-question"
                      value={question}
                      onChange={(event) => setQuestion(event.target.value)}
                      maxLength={1000}
                      rows={5}
                      placeholder="What risks did management identify for its data center business?"
                      className="mt-2 resize-none"
                    />
                    <div className="mt-1 text-right font-mono text-[10px] text-muted-foreground">
                      {question.length}/1000
                    </div>
                  </div>
                  <Button
                    type="submit"
                    disabled={loading || !question.trim() || selected.length === 0}
                    className="gap-2"
                  >
                    {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    {loading ? 'Searching filings…' : 'Ask Arcus Research'}
                  </Button>
                </form>
              </Card>

              {error && (
                <div role="alert" className="flex gap-3 rounded-xl border border-destructive/30 bg-destructive/10 p-4 text-sm text-destructive">
                  <AlertCircle size={18} className="flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {result && (
                <Card className="p-5">
                  <div className="mb-4 flex items-center justify-between gap-3">
                    <h2 className="font-display font-semibold text-foreground">Answer</h2>
                    <span className="font-mono text-[10px] text-muted-foreground">
                      {(result.latency_ms / 1000).toFixed(2)}s · {result.remaining_today} left today
                    </span>
                  </div>
                  <ResearchAnswer answer={result.answer} citations={result.citations} />
                </Card>
              )}
            </div>

            <aside className="space-y-4">
              <Card className="p-4">
                <h2 className="font-display text-sm font-semibold text-foreground">Your indexed holdings</h2>
                <p className="mt-1 text-xs text-muted-foreground">Choose which companies to search.</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {portfolioTickers.map((ticker) => {
                    const active = selected.includes(ticker);
                    return (
                      <button
                        key={ticker}
                        type="button"
                        aria-pressed={active}
                        onClick={() => toggleTicker(ticker)}
                        className={`rounded-full border px-3 py-1.5 font-mono text-xs transition-colors ${
                          active
                            ? 'border-primary bg-primary/15 text-primary'
                            : 'border-border text-muted-foreground hover:border-primary/40'
                        }`}
                      >
                        {ticker}
                      </button>
                    );
                  })}
                </div>
              </Card>

              <Card className="p-4 text-xs leading-5 text-muted-foreground">
                <div className="font-display text-sm font-semibold text-foreground">Coverage</div>
                <p className="mt-2">Latest 10-K: Item 1, Item 1A, and Item 7.</p>
                <p className="mt-1">Latest two earnings releases filed as 8-K Exhibit 99.1.</p>
                <p className="mt-3">20 questions per browser each UTC day.</p>
              </Card>
            </aside>
          </div>
        )}
      </div>
    </AppLayout>
  );
};

export default Research;

