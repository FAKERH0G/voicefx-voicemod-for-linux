import unittest
from unittest.mock import call, patch

from voicemod_for_linux.pipewire import PipeWireRouting, RecordingStream


class PipeWireRoutingTests(unittest.TestCase):
    @patch.object(PipeWireRouting, "_run")
    def test_creates_virtual_sink_and_microphone(self, run):
        run.side_effect = [
            "",
            "314",
            "0\tvoicefx_output.monitor\tPipeWire",
            "315",
            None,
            None,
        ]
        routing = PipeWireRouting()
        routing.ensure_virtual_microphone()

        self.assertEqual(
            run.call_args_list,
            [
                call("list", "short", "sinks"),
                call(
                    "load-module",
                    "module-null-sink",
                    "sink_name=voicefx_output",
                    "sink_properties=device.description=VoiceFX_Output",
                ),
                call("list", "short", "sources"),
                call(
                    "load-module",
                    "module-remap-source",
                    "source_name=voicefx_mic",
                    "master=voicefx_output.monitor",
                    "source_properties=device.description=VoiceFX_Microphone",
                ),
            ],
        )
        routing.close()
        self.assertEqual(
            run.call_args_list[-2:],
            [call("unload-module", "315"), call("unload-module", "314")],
        )

    @patch.object(PipeWireRouting, "_run")
    def test_reuses_existing_virtual_devices(self, run):
        run.side_effect = [
            "0\tvoicefx_output\tPipeWire",
            "0\tvoicefx_mic\tPipeWire",
        ]
        routing = PipeWireRouting()
        routing.ensure_virtual_microphone()
        routing.close()
        self.assertEqual(run.call_count, 2)

    @patch.object(PipeWireRouting, "_run")
    def test_monitor_routes_to_the_system_output_and_can_stop(self, run):
        run.side_effect = [
            "0\tvoicefx_output\tPipeWire",
            "0\tvoicefx_mic\tPipeWire",
            "headphones",
            "416",
            None,
        ]
        routing = PipeWireRouting()
        routing.start_monitor()
        self.assertEqual(
            run.call_args_list[-2:],
            [
                call("get-default-sink"),
                call(
                    "load-module",
                    "module-loopback",
                    "source=voicefx_output.monitor",
                    "sink=headphones",
                    "latency_msec=80",
                ),
            ],
        )
        routing.stop_monitor()
        routing.close()
        self.assertIn(call("unload-module", "416"), run.call_args_list)

    @patch.object(PipeWireRouting, "_run")
    def test_refuses_to_monitor_back_into_the_virtual_sink(self, run):
        run.side_effect = ["0\tvoicefx_output\tPipeWire", "0\tvoicefx_mic\tPipeWire", "voicefx_output"]
        routing = PipeWireRouting()
        with self.assertRaisesRegex(RuntimeError, "headphones"):
            routing.start_monitor()

    @patch.object(PipeWireRouting, "_run")
    def test_default_source_is_restored_only_if_still_owned(self, run):
        run.side_effect = [
            "physical_mic",
            "",
            "voicefx_mic",
            "",
        ]
        routing = PipeWireRouting()
        routing.set_default_source()
        routing.restore_default_source()
        self.assertEqual(
            run.call_args_list,
            [
                call("get-default-source"),
                call("set-default-source", "voicefx_mic"),
                call("get-default-source"),
                call("set-default-source", "physical_mic"),
            ],
        )

    @patch.object(PipeWireRouting, "_run")
    def test_does_not_override_a_new_default_source_selected_by_user(self, run):
        run.side_effect = ["physical_mic", "", "other_mic"]
        routing = PipeWireRouting()
        routing.set_default_source()
        routing.restore_default_source()
        self.assertNotIn(call("set-default-source", "physical_mic"), run.call_args_list)

    @patch.object(PipeWireRouting, "recording_streams")
    @patch.object(PipeWireRouting, "_run")
    def test_routes_and_restores_an_active_call_stream(self, run, streams):
        streams.side_effect = [
            [RecordingStream(123, "Discord", "physical_mic")],
            [RecordingStream(123, "Discord", "voicefx_mic")],
        ]
        routing = PipeWireRouting()
        routing.route_recording_stream(123)
        routing.restore_recording_stream(123)
        self.assertEqual(
            run.call_args_list,
            [
                call("move-source-output", "123", "voicefx_mic"),
                call("move-source-output", "123", "physical_mic"),
            ],
        )

    @patch.object(PipeWireRouting, "recording_streams")
    @patch.object(PipeWireRouting, "_run")
    def test_restore_does_not_override_app_microphone_changed_by_user(self, run, streams):
        streams.side_effect = [
            [RecordingStream(123, "Discord", "physical_mic")],
            [RecordingStream(123, "Discord", "other_mic")],
        ]
        routing = PipeWireRouting()
        routing.route_recording_stream(123)
        routing.restore_recording_stream(123)
        self.assertEqual(run.call_args_list, [call("move-source-output", "123", "voicefx_mic")])

    @patch.object(PipeWireRouting, "recording_streams")
    @patch.object(PipeWireRouting, "_run")
    def test_close_restores_routed_apps_default_mic_and_modules(self, run, streams):
        streams.return_value = [RecordingStream(123, "Discord", "voicefx_mic")]
        routing = PipeWireRouting()
        routing._routed_streams[123] = "physical_mic"
        routing._previous_default_source = "physical_mic"
        routing._modules = ["314", "315", "416"]
        run.return_value = ""
        run.side_effect = [
            "",
            "voicefx_mic",
            "",
            "",
            "",
            "",
        ]

        self.assertEqual(routing.close(), [])
        self.assertEqual(
            run.call_args_list,
            [
                call("move-source-output", "123", "physical_mic"),
                call("get-default-source"),
                call("set-default-source", "physical_mic"),
                call("unload-module", "416"),
                call("unload-module", "315"),
                call("unload-module", "314"),
            ],
        )

    @patch.object(PipeWireRouting, "_json_list")
    def test_lists_app_capture_streams_and_omits_voicefx(self, json_list):
        json_list.side_effect = [
            [{"index": 17, "name": "physical_mic"}],
            [
                {
                    "index": 123,
                    "source": 17,
                    "properties": {
                        "application.name": "Discord",
                        "application.process.binary": "discord",
                    },
                },
                {
                    "index": 124,
                    "source": 17,
                    "properties": {"media.name": "VoiceFX_Microphone input"},
                },
            ],
        ]
        self.assertEqual(
            PipeWireRouting().recording_streams(),
            [RecordingStream(123, "Discord", "physical_mic")],
        )


if __name__ == "__main__":
    unittest.main()
