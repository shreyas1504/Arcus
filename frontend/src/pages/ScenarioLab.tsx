import { Compass } from 'lucide-react';

import AppLayout from '@/components/AppLayout';
import BackButton from '@/components/BackButton';
import { Card } from '@/components/ui/card';

const ScenarioLab = () => (
  <AppLayout title="Scenario Lab">
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
      <BackButton to="/dashboard" label="Back to Dashboard" />

      <div className="mb-6 flex items-start gap-3">
        <div className="rounded-xl border border-primary/20 bg-primary/10 p-2.5">
          <Compass className="text-primary" size={22} />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground">Scenario Lab</h1>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-muted-foreground">
            Ask what happens to your portfolio if an event occurs. Answers come from real
            historical precedents and your holdings, never from a language model's guess.
          </p>
        </div>
      </div>

      <Card className="p-8 text-center">
        <h2 className="font-display font-semibold text-foreground">Coming soon</h2>
        <p className="mx-auto mt-2 max-w-md text-sm text-muted-foreground">
          Scenario Lab is being built and tested. It will appear here once its accuracy checks pass.
        </p>
      </Card>
    </div>
  </AppLayout>
);

export default ScenarioLab;
