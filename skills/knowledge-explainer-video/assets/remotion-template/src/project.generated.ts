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
    background: '#087cf0',
    paper: '#fffdf4',
    ink: '#101820',
    accent: '#ffd51f',
    secondary: '#18c7c9',
    fontFamily: 'Microsoft YaHei UI, Microsoft YaHei, sans-serif',
    borderRadius: 28,
    strokeWidth: 5,
  },
  voiceover: {mode: 'manual', path: null, publicPath: null, durationSec: null, locked: false},
  assets: [],
  scenes: [
    {
      sceneId: 'S001',
      title: '等待项目清单',
      startSec: 0,
      durationSec: 12,
      narrationIds: [],
      anchor: {anchorId: 'topic-card', label: '主题与资料', box: {x: 0.32, y: 0.26, width: 0.36, height: 0.38}},
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
