export type Box = {x: number; y: number; width: number; height: number};

export type Asset = {
  assetId: string;
  kind: string;
  path?: string | null;
  publicPath?: string | null;
  selected?: boolean;
  sourceId?: string | null;
  license?: string | null;
};

export type VisualBeat = {
  beatId: string;
  kind: 'illustration' | 'character' | 'real-video' | 'screenshot' | 'diagram' | 'text-card';
  assetId?: string | null;
  startSec: number;
  durationSec: number;
  box: Box;
  text?: string | null;
  emphasis?: 'key' | 'normal' | string;
  sourceInSec?: number;
  sourceOutSec?: number;
  playbackRate?: number;
};

export type Scene = {
  sceneId: string;
  title: string;
  startSec: number;
  durationSec: number;
  narrationIds: string[];
  anchor?: {anchorId: string; label: string; box: Box} | null;
  visualBeats: VisualBeat[];
  transitionOut?: {mode: 'continuity' | 'section-reset'; anchorId?: string | null; durationSec: number} | null;
};

export type NarrationSentence = {
  narrationId: string;
  text: string;
  purpose: string;
  evidenceIds: string[];
  targetDurationSec: number;
  startSec?: number | null;
  endSec?: number | null;
};

export type ProjectManifest = {
  projectId: string;
  topic: string;
  audience: string;
  status: string;
  format: {fps: number; width: number; height: number; targetDurationSec: number; variants: unknown[]};
  narrative: {structure: string; activeScriptVersion: string; sentences: NarrationSentence[]};
  design: {
    background: string;
    paper: string;
    ink: string;
    accent: string;
    secondary: string;
    fontFamily: string;
    borderRadius: number;
    strokeWidth: number;
  };
  voiceover: {mode: 'manual'; path?: string | null; publicPath?: string | null; durationSec?: number | null; locked: boolean};
  assets: Asset[];
  scenes: Scene[];
};
