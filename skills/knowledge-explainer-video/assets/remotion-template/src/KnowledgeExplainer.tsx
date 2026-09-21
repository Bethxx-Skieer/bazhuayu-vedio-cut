import React from 'react';
import {Audio, Video} from '@remotion/media';
import {
  AbsoluteFill,
  Img,
  Sequence,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';
import {project} from './project.generated';
import type {Asset, Box, Scene, VisualBeat} from './types';

const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

const boxStyle = (box: Box, width: number, height: number): React.CSSProperties => ({
  position: 'absolute',
  left: box.x * width,
  top: box.y * height,
  width: box.width * width,
  height: box.height * height,
});

const assets = new Map(project.assets.map((asset) => [asset.assetId, asset]));

const MediaBeat: React.FC<{beat: VisualBeat; asset?: Asset}> = ({beat, asset}) => {
  const {fps, width, height} = useVideoConfig();
  const frame = useCurrentFrame();
  const start = beat.startSec * fps;
  const end = (beat.startSec + beat.durationSec) * fps;
  const fadeFrames = Math.min(0.4 * fps, beat.durationSec * fps * 0.2);
  const opacity = interpolate(frame, [start, start + fadeFrames, end - fadeFrames, end], [0, 1, 1, 0], clamp);
  if (frame < start || frame > end) return null;

  const common: React.CSSProperties = {
    ...boxStyle(beat.box, width, height),
    opacity,
    overflow: 'hidden',
    border: `${project.design.strokeWidth}px solid ${project.design.ink}`,
    borderRadius: project.design.borderRadius,
    boxShadow: `9px 11px 0 ${project.design.ink}`,
    background: project.design.paper,
    boxSizing: 'border-box',
  };

  if (asset?.publicPath && beat.kind === 'real-video') {
    return (
      <div style={common}>
        <Video
          src={staticFile(asset.publicPath)}
          muted
          trimBefore={(beat.sourceInSec ?? 0) * fps}
          playbackRate={beat.playbackRate ?? 1}
          style={{width: '100%', height: '100%', objectFit: 'cover'}}
        />
      </div>
    );
  }
  if (asset?.publicPath && ['illustration', 'character', 'screenshot'].includes(beat.kind)) {
    return (
      <div style={{...common, background: beat.kind === 'character' ? 'transparent' : project.design.paper}}>
        <Img src={staticFile(asset.publicPath)} style={{width: '100%', height: '100%', objectFit: beat.kind === 'character' ? 'contain' : 'cover'}} />
      </div>
    );
  }

  return (
    <div
      style={{
        ...common,
        display: 'grid',
        placeItems: 'center',
        padding: 36,
        color: project.design.ink,
        fontSize: beat.kind === 'text-card' ? 42 : 50,
        fontWeight: 900,
        lineHeight: 1.25,
        textAlign: 'center',
      }}
    >
      {beat.text ?? beat.beatId}
    </div>
  );
};

const AnchorCard: React.FC<{scene: Scene; opacity: number}> = ({scene, opacity}) => {
  const {width, height} = useVideoConfig();
  if (!scene.anchor) return null;
  return (
    <div
      style={{
        ...boxStyle(scene.anchor.box, width, height),
        opacity,
        display: 'grid',
        placeItems: 'center',
        padding: 24,
        boxSizing: 'border-box',
        border: `${project.design.strokeWidth}px solid ${project.design.ink}`,
        borderRadius: project.design.borderRadius,
        background: project.design.paper,
        boxShadow: `9px 11px 0 ${project.design.ink}`,
        color: project.design.ink,
        fontSize: 34,
        fontWeight: 900,
        textAlign: 'center',
        zIndex: 8,
      }}
    >
      {scene.anchor.label}
    </div>
  );
};

const SceneLayer: React.FC<{scene: Scene; previous?: Scene}> = ({scene, previous}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const durationFrames = scene.durationSec * fps;
  const inFrames = (previous?.transitionOut?.durationSec ?? 0) * fps;
  const outFrames = (scene.transitionOut?.durationSec ?? 0) * fps;
  const sceneIn = inFrames ? interpolate(frame, [0, inFrames], [0, 1], clamp) : 1;
  const sceneOut = outFrames ? interpolate(frame, [durationFrames - outFrames, durationFrames], [1, 0], clamp) : 1;
  const anchorIn = inFrames ? interpolate(frame, [inFrames * 0.72, inFrames], [0, 1], clamp) : 1;
  const anchorOut = outFrames
    ? interpolate(frame, [durationFrames - outFrames, durationFrames - outFrames * 0.72], [1, 0], clamp)
    : 1;
  return (
    <AbsoluteFill style={{opacity: sceneIn * sceneOut, background: project.design.background, fontFamily: project.design.fontFamily}}>
      <div style={{position: 'absolute', left: 72, top: 54, color: project.design.paper, fontSize: 54, fontWeight: 900, textShadow: `4px 4px 0 ${project.design.ink}`}}>
        {scene.title}
      </div>
      {scene.visualBeats.map((beat) => <MediaBeat key={beat.beatId} beat={beat} asset={beat.assetId ? assets.get(beat.assetId) : undefined} />)}
      <AnchorCard scene={scene} opacity={anchorIn * anchorOut} />
    </AbsoluteFill>
  );
};

const MorphTransition: React.FC<{from: Scene; to: Scene}> = ({from, to}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  if (!from.anchor || !to.anchor || !from.transitionOut) return null;
  const duration = from.transitionOut.durationSec * fps;
  const progress = interpolate(frame, [0, duration], [0, 1], clamp);
  const oldOpacity = interpolate(progress, [0.35, 0.52], [1, 0], clamp);
  const newOpacity = interpolate(progress, [0.48, 0.68], [0, 1], clamp);
  const box: Box = {
    x: interpolate(progress, [0, 1], [from.anchor.box.x, to.anchor.box.x], clamp),
    y: interpolate(progress, [0, 1], [from.anchor.box.y, to.anchor.box.y], clamp),
    width: interpolate(progress, [0, 1], [from.anchor.box.width, to.anchor.box.width], clamp),
    height: interpolate(progress, [0, 1], [from.anchor.box.height, to.anchor.box.height], clamp),
  };
  return (
    <div
      style={{
        ...boxStyle(box, width, height),
        display: 'grid',
        placeItems: 'center',
        padding: 24,
        boxSizing: 'border-box',
        border: `${project.design.strokeWidth}px solid ${project.design.ink}`,
        borderRadius: project.design.borderRadius,
        background: project.design.paper,
        boxShadow: `${interpolate(progress, [0, 0.5, 1], [6, 16, 9], clamp)}px ${interpolate(progress, [0, 0.5, 1], [8, 20, 11], clamp)}px 0 ${project.design.ink}`,
        color: project.design.ink,
        fontSize: 34,
        fontWeight: 900,
        textAlign: 'center',
        zIndex: 30,
      }}
    >
      <div style={{gridArea: '1 / 1', opacity: oldOpacity}}>{from.anchor.label}</div>
      <div style={{gridArea: '1 / 1', opacity: newOpacity}}>{to.anchor.label}</div>
    </div>
  );
};

const CaptionLayer: React.FC = () => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;
  const sentence = project.narrative.sentences.find((item) =>
    item.startSec != null && item.endSec != null && seconds >= item.startSec && seconds < item.endSec,
  );
  if (!sentence) return null;
  return (
    <div
      style={{
        position: 'absolute',
        left: 240,
        right: 240,
        bottom: 48,
        padding: '18px 32px',
        border: `${project.design.strokeWidth}px solid ${project.design.ink}`,
        borderRadius: 22,
        background: project.design.paper,
        color: project.design.ink,
        boxShadow: `7px 8px 0 ${project.design.ink}`,
        fontFamily: project.design.fontFamily,
        fontSize: 31,
        fontWeight: 800,
        lineHeight: 1.35,
        textAlign: 'center',
        zIndex: 60,
      }}
    >
      {sentence.text}
    </div>
  );
};

export const KnowledgeExplainer: React.FC = () => {
  const {fps} = useVideoConfig();
  return (
    <AbsoluteFill style={{background: project.design.background}}>
      {project.scenes.map((scene, index) => (
        <Sequence key={scene.sceneId} from={Math.round(scene.startSec * fps)} durationInFrames={Math.ceil(scene.durationSec * fps)}>
          <SceneLayer scene={scene} previous={project.scenes[index - 1]} />
        </Sequence>
      ))}
      {project.scenes.slice(0, -1).map((scene, index) => {
        const transition = scene.transitionOut;
        const next = project.scenes[index + 1];
        if (!transition || transition.mode !== 'continuity') return null;
        return (
          <Sequence
            key={`${scene.sceneId}-${next.sceneId}`}
            from={Math.round(next.startSec * fps)}
            durationInFrames={Math.ceil(transition.durationSec * fps)}
          >
            <MorphTransition from={scene} to={next} />
          </Sequence>
        );
      })}
      <CaptionLayer />
      {project.voiceover.publicPath ? <Audio src={staticFile(project.voiceover.publicPath)} /> : null}
    </AbsoluteFill>
  );
};
