from ..app.audio_detect import parse_volume_output, parse_silence_output

raw_volume_output = '''
    [Parsed_volumedetect_0 @ 0x679a9c0] n_samples: 466944
    [Parsed_volumedetect_0 @ 0x679a9c0] mean_volume: -27.2 dB
    [Parsed_volumedetect_0 @ 0x679a9c0] max_volume: -10.6 dB
    [Parsed_volumedetect_0 @ 0x679a9c0] histogram_10db: 4
    [Parsed_volumedetect_0 @ 0x679a9c0] histogram_11db: 45
    [Parsed_volumedetect_0 @ 0x679a9c0] histogram_12db: 109
    [Parsed_volumedetect_0 @ 0x679a9c0] histogram_13db: 249
    [Parsed_volumedetect_0 @ 0x679a9c0] histogram_14db: 486
    '''

raw_silence_output = '''
    Stream mapping:
      Stream #0:1 (aac) -> volumedetect
      silencedetect -> Stream #0:0 (pcm_s16le)
    Press [q] to stop, [?] for help
    Output #0, null, to 'pipe:':
      Metadata:
        encoder         : Lavf58.35.104
        Stream #0:0: Audio: pcm_s16le, 48000 Hz, stereo, s16, 1536 kb/s
        Metadata:
          encoder         : Lavc58.66.100 pcm_s16le
    [silencedetect @ 0x679adc0] silence_start: 1.33494
    [silencedetect @ 0x679adc0] silence_end: 1.84523 | silence_duration: 0.510292
    [silencedetect @ 0x679adc0] silence_start: 3.52498
    [silencedetect @ 0x679adc0] silence_end: 3.85456 | silence_duration: 0.329583
    '''


def test_parse_volumedetect_output():
    rv = parse_volume_output(raw_volume_output.splitlines())
    assert rv == (-27.2, -10.6)


def test_parse_silencedetect_output():
    rv = parse_silence_output(raw_silence_output.splitlines())
    assert rv == [(1.33494, 1.84523), (3.52498, 3.85456)]
