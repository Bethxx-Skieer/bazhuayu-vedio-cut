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
import {customScenes, customTransitions} from './CustomScenes';
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

  const framed = beat.surface === 'panel';
  const common: React.CSSProperties = {
    ...boxStyle(beat.box, width, height),
    opacity,
    overflow: framed ? 'hidden' : 'visible',
    border: framed ? `${project.design.strokeWidth}px solid ${project.design.ink}` : undefined,
    borderRadius: framed ? project.design.borderRadius : undefined,
    boxShadow: framed ? `4px 5px 0 ${project.design.ink}18` : undefined,
    background: framed ? project.design.paper : 'transparent',
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
      <div style={common}>
        <Img src={staticFile(asset.publicPath)} style={{width: '100%', height: '100%', objectFit: beat.kind === 'screenshot' ? 'cover' : 'contain'}} />
      </div>
    );
  }

  return (
    <div
      style={{
        ...common,
        display: 'grid',
        placeItems: 'center',
        padding: framed ? 24 : 0,
        color: project.design.ink,
        fontSize: beat.kind === 'text-card' ? 36 : 42,
        fontWeight: 700,
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
        padding: scene.anchor.surface === 'panel' ? 18 : 0,
        boxSizing: 'border-box',
        border: scene.anchor.surface === 'panel' ? `${project.design.strokeWidth}px solid ${project.design.ink}` : undefined,
        borderRadius: scene.anchor.surface === 'panel' ? project.design.borderRadius : undefined,
        background: scene.anchor.surface === 'panel' ? project.design.paper : 'transparent',
        color: project.design.ink,
        fontSize: 32,
        fontWeight: 700,
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
  const anchorIn = inFrames ? interpolate(frame, [inFrames * 0.72, inFrames], [0, 1], clamp) : 1;
  const anchorOut = outFrames
    ? interpolate(frame, [durationFrames - outFrames, durationFrames - outFrames * 0.72], [1, 0], clamp)
    : 1;
  const CustomScene = customScenes[scene.sceneId];
  return (
    <AbsoluteFill style={{clipPath: `inset(0 ${(1 - sceneIn) * 100}% 0 0)`, background: project.design.background, fontFamily: project.design.fontFamily}}>
      {CustomScene ? <CustomScene scene={scene} localFrame={frame} /> : (
        <>
          <div style={{position: 'absolute', left: 72, top: 54, color: project.design.ink, fontSize: 28, fontWeight: 650}}>
            {scene.title}
          </div>
          {scene.visualBeats.map((beat) => <MediaBeat key={beat.beatId} beat={beat} asset={beat.assetId ? assets.get(beat.assetId) : undefined} />)}
          <AnchorCard scene={scene} opacity={anchorIn * anchorOut} />
        </>
      )}
    </AbsoluteFill>
  );
};

const MorphTransition: React.FC<{from: Scene; to: Scene}> = ({from, to}) => {
  const frame = useCurrentFrame();
  const {fps, width, height} = useVideoConfig();
  if (!from.anchor || !to.anchor || !from.transitionOut) return null;
  const duration = from.transitionOut.durationSec * fps;
  const progress = interpolate(frame, [0, duration], [0, 1], clamp);
  const CustomTransition = customTransitions[from.sceneId];
  if (CustomTransition) return <CustomTransition from={from} to={to} progress={progress} />;
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
        padding: from.anchor.surface === 'panel' || to.anchor.surface === 'panel' ? 18 : 0,
        boxSizing: 'border-box',
        border: from.anchor.surface === 'panel' || to.anchor.surface === 'panel' ? `${project.design.strokeWidth}px solid ${project.design.ink}` : undefined,
        borderRadius: from.anchor.surface === 'panel' || to.anchor.surface === 'panel' ? project.design.borderRadius : undefined,
        background: from.anchor.surface === 'panel' || to.anchor.surface === 'panel' ? project.design.paper : 'transparent',
        color: project.design.ink,
        fontSize: 32,
        fontWeight: 700,
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
  if (!project.captions?.enabled) return null;
  const milliseconds = frame / fps * 1000;
  const cue = project.captions.cues?.find((item) => milliseconds >= item.startMs && milliseconds < item.endMs);
  if (!cue) return null;
  const style = project.captions.style;
  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        translate: '-50% 0',
        width: 'max-content',
        maxWidth: style?.maxWidth ?? 1400,
        bottom: style?.bottom ?? 42,
        padding: '2px 12px',
        color: project.design.ink,
        WebkitTextStroke: `1px ${project.design.paper}`,
        textShadow: `0 1px 4px ${project.design.paper}`,
        fontFamily: project.design.fontFamily,
        fontSize: style?.fontSize ?? 40,
        fontWeight: 650,
        lineHeight: 1.25,
        textAlign: 'center',
        zIndex: 60,
      }}
    >
      {cue.text}
    </div>
  );
};

export const KnowledgeExplainer: React.FC = () => {
  const {fps} = useVideoConfig();
  const finalStatuses = new Set(['timeline_locked', 'preview_approved', 'rendered', 'qa_passed', 'delivered']);
  if (project.schemaVersion === '1.1' && finalStatuses.has(project.status)) {
    const unfinished = project.scenes.filter((scene) =>
      scene.visualBeats.every((beat) =>
        (beat.kind === 'diagram' || beat.kind === 'text-card') && !beat.assetId,
      ) && !customScenes[scene.sceneId],
    );
    if (unfinished.length) {
      throw new Error(`Purpose-built visual scene required before rendering: ${unfinished.map((scene) => scene.sceneId).join(', ')}`);
    }
  }
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
      {project.music?.enabled && project.music.publicPath ? (
        <Audio
          src={staticFile(project.music.publicPath)}
          loop
          volume={(audioFrame) => {
            const seconds = audioFrame / fps;
            const gain = project.music?.gain ?? 0.18;
            if (!project.music?.ducking) return gain;
            const distance = project.narrative.sentences.reduce((best, sentence) => {
              if (sentence.startSec == null || sentence.endSec == null) return best;
              return Math.min(best, Math.max(sentence.startSec - seconds, seconds - sentence.endSec, 0));
            }, Infinity);
            return gain * interpolate(distance, [0, 0.3], [0.55, 1], clamp);
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};
