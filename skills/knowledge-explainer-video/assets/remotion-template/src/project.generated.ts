import type {ProjectManifest} from './types';

export const project = {
  projectId: 'template-preview',
  topic: '知识讲解视频模板',
  audience: '普通观众',
  status: 'visual_direction_approved',
  format: {fps: 30, width: 1920, height: 1080, targetDurationSec: 12, variants: []},
  narrative: {
    structure: 'concept-explainer',
    activeScriptVersion: 'v1',
    sentences: [],
  },
  design: {
    background: '#faf9f5',
    paper: '#fffdf8',
    ink: '#273630',
    accent: '#bf7949',
    secondary: '#688a77',
    fontFamily: 'Microsoft YaHei UI, Microsoft YaHei, sans-serif',
    borderRadius: 18,
    strokeWidth: 2,
  },
  voiceover: {mode: 'manual', path: null, publicPath: null, durationSec: null, locked: false},
  captions: {enabled: false},
  music: {enabled: false},
  assets: [],
  scenes: [
    {
      sceneId: 'S001',
      title: '等待项目清单',
      startSec: 0,
      durationSec: 12,
      narrationIds: [],
      anchor: null,
      visualBeats: [
        {
          beatId: 'B001',
          kind: 'diagram',
          assetId: null,
          startSec: 0.5,
          durationSec: 11,
          box: {x: 0.12, y: 0.2, width: 0.76, height: 0.56},
          text: '主题 → 证据 → 讲稿 → 丰富画面 → 完整视频',
          emphasis: 'key',
        },
      ],
      transitionOut: null,
    },
  ],
} as ProjectManifest;
