"""Audio on disk: downloading, naming, and ffmpeg-based conversion."""

# A real podcast episode is never this small; anything under it is a failed
# download or an ffmpeg run that died before encoding anything.
MIN_AUDIO_BYTES = 100 * 1024

# Archive formats we may already hold for an episode, in preference order.
AUDIO_EXTENSIONS = (".ogg", ".mp3")
