import fs from 'node:fs/promises';
import { Innertube } from 'youtubei.js';

const COOKIE_PATH =
  process.env.APOLLO_YOUTUBE_COOKIE_PATH || '/config/youtube-cookie.txt';

function text(value) {
  if (value == null) return null;
  if (typeof value === 'string') return value;
  if (typeof value?.text === 'string') return value.text;
  if (typeof value?.content === 'string') return value.content;
  if (typeof value?.toString === 'function') {
    const out = value.toString();
    if (out && out !== '[object Object]') return out;
  }
  return null;
}

function thumbnails(value) {
  const source =
    (Array.isArray(value?.image) ? value.image : null) ??
    value?.thumbnails ??
    value?.image?.sources ??
    value?.sources ??
    value?.primary_thumbnail?.image ??
    [];

  if (!Array.isArray(source)) return [];

  return source
    .map((item) => ({
      url: item?.url ?? null,
      width: item?.width ?? null,
      height: item?.height ?? null
    }))
    .filter((item) => item.url);
}

function progressFrom(item) {
  const modern = item?.content_image?.overlays ?? [];

  for (const overlay of modern) {
    const percent = overlay?.progress_bar?.start_percent;
    if (typeof percent === 'number') return percent;
  }

  const legacy = item?.thumbnail_overlays ?? [];

  for (const overlay of legacy) {
    const percent =
      overlay?.percent_duration_watched ??
      overlay?.start_percent ??
      overlay?.progress_percent ??
      overlay?.percent;

    if (typeof percent === 'number') return percent;
  }

  return null;
}

function startSecondsFrom(item) {
  const candidates = [
    item?.renderer_context?.command_context?.on_tap?.payload?.startTimeSeconds,
    item?.renderer_context?.command_context?.on_tap?.innertube_command
      ?.watch_endpoint?.start_time_seconds,
    item?.navigation_endpoint?.watch_endpoint?.start_time_seconds
  ];

  for (const value of candidates) {
    const parsed = Number(value);
    if (Number.isFinite(parsed) && parsed >= 0) return parsed;
  }

  return null;
}

function normalize(item) {
  if (!item) return null;

  if (item?.constructor?.name === 'RichItem' && item?.content) {
    item = item.content;
  }

  const type = item?.constructor?.name ?? 'Unknown';

  // Apollo intentionally excludes Shorts and non-video feed wrappers.
  if (
    type === 'ShortsLockupView' ||
    type === 'RichShelf' ||
    type === 'ContinuationItem'
  ) {
    return null;
  }

  const id =
    item?.content_id ??
    item?.video_id ??
    item?.id ??
    item?.endpoint?.payload?.videoId ??
    null;

  if (!id) return null;

  // Exclude YouTube Mix / radio playlist entries.
  if (String(id).startsWith('RD')) return null;

  const metadata = item?.metadata ?? item?.lockup_metadata_view_model ?? {};

  const title =
    text(metadata?.title) ??
    text(metadata?.title?.content) ??
    text(item?.title);

  const rows =
    metadata?.metadata?.metadata_rows ??
    metadata?.metadata?.content_metadata_view_model?.metadata_rows ??
    [];

  const channel =
    text(rows?.[0]?.metadata_parts?.[0]?.text) ??
    text(metadata?.subtitle) ??
    text(item?.author?.name) ??
    text(item?.author);

  const durationBadge =
    item?.content_image?.overlays
      ?.flatMap((overlay) => overlay?.badges ?? [])
      ?.find((badge) => /^\d+(?::\d+){1,2}$/.test(text(badge?.text) ?? ''));

  const duration =
    text(durationBadge?.text) ??
    text(item?.duration?.text) ??
    text(item?.duration);

  const thumbs =
    thumbnails(item?.content_image).length
      ? thumbnails(item?.content_image)
      : thumbnails(item?.thumbnail);

  return {
    video_id: String(id),
    title,
    channel,
    duration,
    thumbnails: thumbs,
    progress_percent: progressFrom(item),
    start_seconds: startSecondsFrom(item)
  };
}

async function createClient() {
  const cookie = (await fs.readFile(COOKIE_PATH, 'utf8')).trim();

  if (!cookie) {
    throw new Error('YouTube cookie file is empty');
  }

  return Innertube.create({
    cookie,
    client_type: 'WEB',
    location: 'US'
  });
}

async function status() {
  try {
    const stat = await fs.stat(COOKIE_PATH);
    return {
      configured: stat.isFile() && stat.size > 0,
      cookie_path: COOKIE_PATH
    };
  } catch {
    return {
      configured: false,
      cookie_path: COOKIE_PATH
    };
  }
}

async function feed(kind) {
  const yt = await createClient();

  const page =
    kind === 'history'
      ? await yt.getHistory()
      : await yt.getHomeFeed();

  const source =
    page?.contents?.contents ??
    page?.contents ??
    page?.videos ??
    page?.items ??
    [];

  const items = [];

  for (const item of source) {
    const normalized = normalize(item);
    if (normalized) items.push(normalized);
  }

  return {
    kind,
    count: items.length,
    items
  };
}

async function main() {
  const command = process.argv[2] || 'status';

  if (command === 'status') {
    console.log(JSON.stringify(await status()));
    return;
  }

  if (command === 'home' || command === 'history') {
    console.log(JSON.stringify(await feed(command)));
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

main().catch((error) => {
  console.error(error?.message || String(error));
  process.exit(1);
});
