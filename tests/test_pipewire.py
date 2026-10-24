import unittest
from unittest.mock import call, patch

from voicemod_for_linux.pipewire import PipeWireRouting


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


if __name__ == "__main__":
    unittest.main()
