import type {Caption} from '@remotion/captions';

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
  changeRole?: 'major' | 'micro';
  surface?: 'none' | 'panel';
  sourceInSec?: number;
  sourceOutSec?: number;
  playbackRate?: number;
};

export type StoryAction = {
  question: string;
  concept: string;
  actorId: string | null;
  objectIds: string[];
  action: string;
  outcome: string;
  triggerNarrationId: string;
  startSec: number;
  endSec: number;
  holdSec: number;
};

export type Scene = {
  sceneId: string;
  title: string;
  startSec: number;
  durationSec: number;
  narrationIds: string[];
  storyAction?: StoryAction | null;
  anchor?: {anchorId: string; label: string; box: Box; surface?: 'none' | 'panel'} | null;
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
  schemaVersion?: '1.0' | '1.1';
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
  captions?: {enabled: boolean; sourcePath?: string | null; cues?: Caption[]; style?: {fontSize?: number; bottom?: number; maxWidth?: number; maxLines?: number}};
  music?: {enabled: boolean; path?: string | null; publicPath?: string | null; sourceId?: string | null; license?: string | null; gain?: number; ducking?: boolean};
  assets: Asset[];
  scenes: Scene[];
};
