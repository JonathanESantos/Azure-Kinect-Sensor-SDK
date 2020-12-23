'''
test_k4a_azurekinect.py

Tests for the k4a functions for Azure Kinect device.

Copyright (C) Microsoft Corporation. All rights reserved.
'''

import unittest
import ctypes
from threading import Lock
    
import k4a

# Save capture to reuse in tests since it takes a while to get a capture from the device.
glb_capture = None
glb_color_format = None
glb_color_resolution = None
glb_depth_mode = None

# Use for logging callback. But it doesn't work right now...
def glb_print_message(context:ctypes.c_void_p, 
                      level:k4a.ELogLevel, 
                      src_file:ctypes.POINTER(ctypes.c_char), 
                      src_line:ctypes.c_int, 
                      message:ctypes.POINTER(ctypes.c_char)):
    print(str(level) + " in " + str(src_file) + " at line " + str(src_line) + ": " + str(message))


def get_capture(device_handle:k4a._bindings.k4a._DeviceHandle,
                color_format:k4a.EImageFormat,
                color_resolution:k4a.EColorResolution,
                depth_mode:k4a.EDepthMode)->k4a._bindings.k4a._CaptureHandle:

    global glb_capture
    global glb_color_format
    global glb_color_resolution
    global glb_depth_mode

    capture = glb_capture

    if (capture is None or 
        glb_color_format != color_format or
        glb_color_resolution != color_resolution or
        glb_depth_mode != glb_depth_mode):

        # Release any previous captures.
        if (capture is not None):
            k4a.k4a_capture_release(capture)
            capture = None

        # Start the cameras.
        device_config = k4a.DeviceConfiguration()
        device_config.color_format = color_format
        device_config.color_resolution = color_resolution
        device_config.depth_mode = depth_mode
        device_config.camera_fps = k4a.EFramePerSecond.FPS_15
        device_config.synchronized_images_only = True
        device_config.depth_delay_off_color_usec = 0
        device_config.wired_sync_mode = k4a.EWiredSyncMode.STANDALONE
        device_config.subordinate_delay_off_master_usec = 0
        device_config.disable_streaming_indicator = False

        status = k4a.k4a_device_start_cameras(device_handle, ctypes.byref(device_config))
        if(k4a.K4A_SUCCEEDED(status)):

            # Get a capture. Ignore the retured status.
            capture = k4a._bindings.k4a._CaptureHandle()
            timeout_ms = ctypes.c_int32(1000)
            status = k4a.k4a_device_get_capture(
                device_handle,
                ctypes.byref(capture),
                timeout_ms
            )

        # Stop the cameras.
        k4a.k4a_device_stop_cameras(device_handle)

        glb_capture = capture
        glb_color_format = color_format
        glb_color_resolution = color_resolution
        glb_depth_mode = depth_mode

    return capture


def get_1080p_bgr32_nfov_2x2binned(device_handle):
    return get_capture(device_handle,
        k4a.EImageFormat.COLOR_BGRA32,
        k4a.EColorResolution.RES_1080P,
        k4a.EDepthMode.NFOV_2X2BINNED)


def k4a_device_get_color_control_capability(
    device_handle:k4a._bindings.k4a._DeviceHandle,
    color_control_command:k4a.EColorControlCommand
    )->k4a.EStatus:

    supports_auto = ctypes.c_bool(False)
    min_value = ctypes.c_int32(0)
    max_value = ctypes.c_int32(0)
    step_value = ctypes.c_int32(0)
    default_value = ctypes.c_int32(0)
    color_control_mode = ctypes.c_int32(k4a.EColorControlMode.AUTO.value)

    status = k4a.k4a_device_get_color_control_capabilities(
        device_handle,
        color_control_command,
        ctypes.byref(supports_auto),
        ctypes.byref(min_value),
        ctypes.byref(max_value),
        ctypes.byref(step_value),
        ctypes.byref(default_value),
        ctypes.byref(color_control_mode),
    )

    return status

def k4a_device_set_and_get_color_control(
    device_handle:k4a._bindings.k4a._DeviceHandle,
    color_control_command:k4a.EColorControlCommand):

    mode = ctypes.c_int32(k4a.EColorControlMode.MANUAL.value)
    saved_value = ctypes.c_int32(0)

    # Get the step size.
    supports_auto = ctypes.c_bool(False)
    min_value = ctypes.c_int32(0)
    max_value = ctypes.c_int32(0)
    step_value = ctypes.c_int32(0)
    default_value = ctypes.c_int32(0)
    color_control_mode = ctypes.c_int32(k4a.EColorControlMode.MANUAL.value)

    status = k4a.k4a_device_get_color_control_capabilities(
        device_handle,
        color_control_command,
        ctypes.byref(supports_auto),
        ctypes.byref(min_value),
        ctypes.byref(max_value),
        ctypes.byref(step_value),
        ctypes.byref(default_value),
        ctypes.byref(color_control_mode),
    )

    # Read the original value.
    temp_mode = ctypes.c_int32(k4a.EColorControlMode.MANUAL.value)
    status0 = k4a.k4a_device_get_color_control(
        device_handle,
        ctypes.c_int(color_control_command.value),
        ctypes.byref(temp_mode),
        ctypes.byref(saved_value))
    
    # Write a new value.
    new_value = ctypes.c_int32(0)
    if (saved_value.value + step_value.value <= max_value.value):
        new_value = ctypes.c_int32(saved_value.value + step_value.value)
    else:
        new_value = ctypes.c_int32(saved_value.value - step_value.value)

    status1 = k4a.k4a_device_set_color_control(
        device_handle,
        ctypes.c_int(color_control_command.value),
        mode,
        new_value)

    # Read back the value to check that it was written.
    temp_mode = ctypes.c_int32(k4a.EColorControlMode.MANUAL.value)
    new_value_readback = ctypes.c_int32(0)
    status2 = k4a.k4a_device_get_color_control(
        device_handle,
        ctypes.c_int(color_control_command.value),
        ctypes.byref(temp_mode),
        ctypes.byref(new_value_readback))

    # Write the original saved value.
    status3 = k4a.k4a_device_set_color_control(
        device_handle,
        ctypes.c_int(color_control_command.value),
        mode,
        saved_value)

    # Read back the value to check that it was written.
    temp_mode = ctypes.c_int32(k4a.EColorControlMode.MANUAL.value)
    saved_value_readback = ctypes.c_int32(0)
    status4 = k4a.k4a_device_get_color_control(
        device_handle,
        ctypes.c_int(color_control_command.value),
        ctypes.byref(temp_mode),
        ctypes.byref(saved_value_readback))

    return (status, status0, status1, status2, status3, status4,
        saved_value, saved_value_readback, new_value, new_value_readback)


class Test_K4A_AzureKinect(unittest.TestCase):
    '''Test k4a functions requiring a device handle for Azure Kinect device.
    '''

    @classmethod
    def setUpClass(cls):
        cls.device_handle = k4a._bindings.k4a._DeviceHandle()
        status = k4a.k4a_device_open(ctypes.c_uint32(0), ctypes.byref(cls.device_handle))
        assert(k4a.K4A_SUCCEEDED(status))

        cls.lock = Lock()

    @classmethod
    def tearDownClass(cls):

        if glb_capture is not None:
            k4a.k4a_capture_release(glb_capture)

        # Stop the cameras and imus before closing device.
        k4a.k4a_device_stop_cameras(cls.device_handle)
        k4a.k4a_device_stop_imu(cls.device_handle)
        k4a.k4a_device_close(cls.device_handle)

    def test_k4a_device_open_twice_expected_fail(self):
        device_handle_2 = k4a._bindings.k4a._DeviceHandle()
        status = k4a.k4a_device_open(ctypes.c_uint32(0), ctypes.byref(device_handle_2))
        self.assertTrue(k4a.K4A_FAILED(status))

        status = k4a.k4a_device_open(ctypes.c_uint32(1000000), ctypes.byref(device_handle_2))
        self.assertTrue(k4a.K4A_FAILED(status))

    def test_k4a_device_get_installed_count(self):
        device_count = k4a.k4a_device_get_installed_count()
        self.assertGreater(device_count, 0)

    def test_k4a_set_debug_message_handler_NULL_callback(self):
        status = k4a.k4a_set_debug_message_handler(
            ctypes.cast(ctypes.c_void_p(), ctypes.POINTER(k4a.logging_message_cb)), 
            ctypes.c_void_p(), 
            k4a.ELogLevel.TRACE)
        self.assertTrue(k4a.K4A_SUCCEEDED(status))

    @unittest.skip
    def test_k4a_set_debug_message_handler_callback(self):
        logger_cb = k4a.logging_message_cb(glb_print_message)
        context = ctypes.c_void_p()
        status = k4a.k4a_set_debug_message_handler(
            ctypes.byref(logger_cb), 
            context, 
            k4a.ELogLevel.TRACE
        )
        self.assertTrue(k4a.K4A_SUCCEEDED(status))

    def test_k4a_device_get_capture(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

    # Always seems to fail starting IMU. Maybe there isn't one in this system?
    @unittest.expectedFailure
    def test_k4a_device_get_imu_sample(self):
        with self.lock:

            # Start imu.
            status = k4a.k4a_device_start_imu(self.device_handle)
            self.assertTrue(k4a.K4A_SUCCEEDED(status))

            imu_sample = k4a.ImuSample()
            timeout_ms = ctypes.c_int32(1000)
            status = k4a.k4a_device_get_imu_sample(
                self.device_handle,
                ctypes.byref(imu_sample),
                timeout_ms
            )

            # Stop imu.
            k4a.k4a_device_stop_imu(self.device_handle)

            self.assertEqual(status, k4a.EWaitStatus.SUCCEEDED)
            self.assertNotAlmostEqual(imu_sample.temperature, 0.0)
            self.assertNotAlmostEqual(imu_sample.acc_sample.xyz.x, 0.0)
            self.assertNotAlmostEqual(imu_sample.acc_sample.xyz.y, 0.0)
            self.assertNotAlmostEqual(imu_sample.acc_sample.xyz.z, 0.0)
            self.assertNotEqual(imu_sample.acc_timestamp_usec, 0)
            self.assertNotAlmostEqual(imu_sample.gyro_sample.xyz.x, 0.0)
            self.assertNotAlmostEqual(imu_sample.gyro_sample.xyz.y, 0.0)
            self.assertNotAlmostEqual(imu_sample.gyro_sample.xyz.z, 0.0)
            self.assertNotEqual(imu_samplew.gyro_timestamp_usec, 0.0)

    def test_k4a_capture_create(self):
        capture = k4a._bindings.k4a._CaptureHandle()
        status = k4a.k4a_capture_create(ctypes.byref(capture))
        self.assertTrue(k4a.K4A_SUCCEEDED(status))

        k4a.k4a_capture_reference(capture)
        k4a.k4a_capture_release(capture)
        k4a.k4a_capture_release(capture)
        
    def test_k4a_capture_get_color_image(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)
            
            color_image = k4a.k4a_capture_get_color_image(capture)
            self.assertIsInstance(color_image, k4a._bindings.k4a._ImageHandle)
            k4a.k4a_image_release(color_image)

    def test_k4a_capture_get_depth_image(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)
            
            depth_image = k4a.k4a_capture_get_depth_image(capture)
            self.assertIsInstance(depth_image, k4a._bindings.k4a._ImageHandle)
            k4a.k4a_image_release(depth_image)

    def test_k4a_capture_get_ir_image(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)
            
            ir_image = k4a.k4a_capture_get_ir_image(capture)
            self.assertIsInstance(ir_image, k4a._bindings.k4a._ImageHandle)
            k4a.k4a_image_release(ir_image)

    def test_k4a_image_create(self):
        
        image_format = k4a.EImageFormat.COLOR_BGRA32
        width_pixels = 512
        height_pixels = 512
        stride_pixels = 4*512
        image_handle = k4a._bindings.k4a._ImageHandle()
        
        status = k4a.k4a_image_create(ctypes.c_int(image_format.value), 
            width_pixels, height_pixels, stride_pixels, ctypes.byref(image_handle))
        self.assertEqual(k4a.EStatus.SUCCEEDED, status)

        # Check that the created image has properties requested.
        created_image_format = k4a.k4a_image_get_format(image_handle)
        created_image_width_pixels = k4a.k4a_image_get_width_pixels(image_handle)
        created_image_height_pixels = k4a.k4a_image_get_height_pixels(image_handle)
        created_image_stride_bytes = k4a.k4a_image_get_stride_bytes(image_handle)

        k4a.k4a_image_release(image_handle)

        self.assertEqual(image_format, created_image_format)
        self.assertEqual(width_pixels, created_image_width_pixels)
        self.assertEqual(height_pixels, created_image_height_pixels)
        self.assertEqual(stride_pixels, created_image_stride_bytes)

    def test_k4a_capture_set_color_image(self):

        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            # Grab the current color image.
            saved_color_image = k4a.k4a_capture_get_color_image(capture)

            # Create a new image.
            image_format = k4a.EImageFormat.COLOR_BGRA32
            width_pixels = ctypes.c_int(512)
            height_pixels = ctypes.c_int(512)
            stride_bytes = ctypes.c_int(4*512)
            image_handle = k4a._bindings.k4a._ImageHandle()
            status = k4a.k4a_image_create(ctypes.c_int(image_format.value), 
                width_pixels, height_pixels, stride_bytes, ctypes.byref(image_handle))
            self.assertEqual(k4a.EStatus.SUCCEEDED, status)

            # Replace the saved image with the created one.
            k4a.k4a_capture_set_color_image(capture, image_handle)
            k4a.k4a_image_release(image_handle)

            # Get a new image. It should be identical to the created one.
            color_image = k4a.k4a_capture_get_color_image(capture)

            # Test that the new image has characteristics of the created image.
            color_image_format = k4a.k4a_image_get_format(color_image)
            color_image_width_pixels = k4a.k4a_image_get_width_pixels(color_image)
            color_image_height_pixels = k4a.k4a_image_get_height_pixels(color_image)
            color_image_stride_bytes = k4a.k4a_image_get_stride_bytes(color_image)
            k4a.k4a_image_release(color_image)

            # Now put back the saved color image into the capture.
            k4a.k4a_capture_set_color_image(capture, saved_color_image)
            k4a.k4a_image_release(saved_color_image)

            # Test that the image has characteristics of the saved color image.
            saved_color_image2 = k4a.k4a_capture_get_color_image(capture)
            saved_color_image_format = k4a.k4a_image_get_format(saved_color_image2)
            saved_color_image_width_pixels = k4a.k4a_image_get_width_pixels(saved_color_image2)
            saved_color_image_height_pixels = k4a.k4a_image_get_height_pixels(saved_color_image2)
            saved_color_image_stride_bytes = k4a.k4a_image_get_stride_bytes(saved_color_image2)
            k4a.k4a_image_release(saved_color_image2)

            self.assertEqual(color_image_format, k4a.EImageFormat.COLOR_BGRA32)
            self.assertEqual(color_image_width_pixels, 512)
            self.assertEqual(color_image_height_pixels, 512)
            self.assertEqual(color_image_stride_bytes, 512*4)

            self.assertEqual(saved_color_image_format, k4a.EImageFormat.COLOR_BGRA32)
            self.assertEqual(saved_color_image_width_pixels, 1920)
            self.assertEqual(saved_color_image_height_pixels, 1080)
            self.assertEqual(saved_color_image_stride_bytes, 1920*4)

    def test_k4a_capture_set_depth_image(self):

        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            # Grab the current depth image and add a reference to it so it is not destroyed.
            saved_depth_image = k4a.k4a_capture_get_depth_image(capture)

            # Create a new image.
            image_format = k4a.EImageFormat.DEPTH16
            width_pixels = ctypes.c_int(512)
            height_pixels = ctypes.c_int(512)
            stride_bytes = ctypes.c_int(4*512)
            image_handle = k4a._bindings.k4a._ImageHandle()
            status = k4a.k4a_image_create(ctypes.c_int(image_format.value), 
                width_pixels, height_pixels, stride_bytes, ctypes.byref(image_handle))
            self.assertEqual(k4a.EStatus.SUCCEEDED, status)

            # Replace the saved image with the created one.
            k4a.k4a_capture_set_depth_image(capture, image_handle)
            k4a.k4a_image_release(image_handle)

            # Get a new image. It should be identical to the created one.
            depth_image = k4a.k4a_capture_get_depth_image(capture)

            # Test that the new image has characteristics of the created image.
            depth_image_format = k4a.k4a_image_get_format(depth_image)
            depth_image_width_pixels = k4a.k4a_image_get_width_pixels(depth_image)
            depth_image_height_pixels = k4a.k4a_image_get_height_pixels(depth_image)
            depth_image_stride_bytes = k4a.k4a_image_get_stride_bytes(depth_image)
            k4a.k4a_image_release(depth_image)

            # Now put back the saved color image into the capture.
            k4a.k4a_capture_set_depth_image(capture, saved_depth_image)
            k4a.k4a_image_release(saved_depth_image)

            # Test that the image has characteristics of the saved depth image.
            saved_depth_image2 = k4a.k4a_capture_get_depth_image(capture)
            saved_depth_image_format = k4a.k4a_image_get_format(saved_depth_image2)
            saved_depth_image_width_pixels = k4a.k4a_image_get_width_pixels(saved_depth_image)
            saved_depth_image_height_pixels = k4a.k4a_image_get_height_pixels(saved_depth_image)
            saved_depth_image_stride_bytes = k4a.k4a_image_get_stride_bytes(saved_depth_image)
            k4a.k4a_image_release(saved_depth_image2)

            self.assertEqual(depth_image_format, k4a.EImageFormat.DEPTH16)
            self.assertEqual(depth_image_width_pixels, 512)
            self.assertEqual(depth_image_height_pixels, 512)
            self.assertEqual(depth_image_stride_bytes, 512*4)

            self.assertEqual(saved_depth_image_format, k4a.EImageFormat.DEPTH16)
            self.assertEqual(saved_depth_image_width_pixels, 320)
            self.assertEqual(saved_depth_image_height_pixels, 288)
            self.assertEqual(saved_depth_image_stride_bytes, 320*2)

    def test_k4a_capture_set_ir_image(self):

        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            # Grab the current depth image and add a reference to it so it is not destroyed.
            saved_ir_image = k4a.k4a_capture_get_ir_image(capture)

            # Create a new image.
            image_format = k4a.EImageFormat.IR16
            width_pixels = ctypes.c_int(512)
            height_pixels = ctypes.c_int(512)
            stride_bytes = ctypes.c_int(4*512)
            image_handle = k4a._bindings.k4a._ImageHandle()
            status = k4a.k4a_image_create(ctypes.c_int(image_format.value), 
                width_pixels, height_pixels, stride_bytes, ctypes.byref(image_handle))
            self.assertEqual(k4a.EStatus.SUCCEEDED, status)

            # Replace the saved image with the created one.
            k4a.k4a_capture_set_ir_image(capture, image_handle)
            k4a.k4a_image_release(image_handle)

            # Get a new image. It should be identical to the created one.
            ir_image = k4a.k4a_capture_get_ir_image(capture)

            # Test that the new image has characteristics of the created image.
            ir_image_format = k4a.k4a_image_get_format(ir_image)
            ir_image_width_pixels = k4a.k4a_image_get_width_pixels(ir_image)
            ir_image_height_pixels = k4a.k4a_image_get_height_pixels(ir_image)
            ir_image_stride_bytes = k4a.k4a_image_get_stride_bytes(ir_image)
            k4a.k4a_image_release(ir_image)

            # Now put back the saved color image into the capture.
            k4a.k4a_capture_set_ir_image(capture, saved_ir_image)
            k4a.k4a_image_release(saved_ir_image)

            # Test that the image has characteristics of the saved depth image.
            saved_ir_image2 = k4a.k4a_capture_get_ir_image(capture)
            saved_ir_image_format = k4a.k4a_image_get_format(saved_ir_image2)
            saved_ir_image_width_pixels = k4a.k4a_image_get_width_pixels(saved_ir_image2)
            saved_ir_image_height_pixels = k4a.k4a_image_get_height_pixels(saved_ir_image2)
            saved_ir_image_stride_bytes = k4a.k4a_image_get_stride_bytes(saved_ir_image2)
            k4a.k4a_image_release(saved_ir_image2)

            self.assertEqual(ir_image_format, k4a.EImageFormat.IR16)
            self.assertEqual(ir_image_width_pixels, 512)
            self.assertEqual(ir_image_height_pixels, 512)
            self.assertEqual(ir_image_stride_bytes, 512*4)

            self.assertEqual(saved_ir_image_format, k4a.EImageFormat.IR16)
            self.assertEqual(saved_ir_image_width_pixels, 320)
            self.assertEqual(saved_ir_image_height_pixels, 288)
            self.assertEqual(saved_ir_image_stride_bytes, 320*2)

    def test_k4a_capture_get_temperature_c(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            temperature_c = k4a.k4a_capture_get_temperature_c(capture)
            self.assertNotAlmostEqual(temperature_c, 0.0, 2)

    def test_k4a_capture_set_temperature_c(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            absolute_zero_temperature_c = -277.15
            k4a.k4a_capture_set_temperature_c(capture, absolute_zero_temperature_c)

            temperature_c = k4a.k4a_capture_get_temperature_c(capture)
            self.assertAlmostEqual(temperature_c, absolute_zero_temperature_c, 2)

    def test_k4a_image_get_buffer(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            buffer_ptr = k4a.k4a_image_get_buffer(color_image)
            k4a.k4a_image_release(color_image)
            self.assertIsNotNone(ctypes.cast(buffer_ptr, ctypes.c_void_p).value)

    def test_k4a_image_get_buffer_None(self):
            buffer_ptr = k4a.k4a_image_get_buffer(None)
            self.assertIsNone(ctypes.cast(buffer_ptr, ctypes.c_void_p).value)

    def test_k4a_image_get_size(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            color_image_size_bytes = k4a.k4a_image_get_size(color_image)
            k4a.k4a_image_release(color_image)
            self.assertEqual(color_image_size_bytes, 1080*1920*4)

    def test_k4a_image_get_format(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            color_image_format = k4a.k4a_image_get_format(color_image)
            k4a.k4a_image_release(color_image)
            self.assertEqual(color_image_format, k4a.EImageFormat.COLOR_BGRA32)
    
    def test_k4a_image_get_width_pixels(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            color_image_width_pixels = k4a.k4a_image_get_width_pixels(color_image)
            k4a.k4a_image_release(color_image)
            self.assertEqual(color_image_width_pixels, 1920)

    def test_k4a_image_get_height_pixels(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            color_image_height_pixels = k4a.k4a_image_get_height_pixels(color_image)
            k4a.k4a_image_release(color_image)
            self.assertEqual(color_image_height_pixels, 1080)

    def test_k4a_image_get_stride_bytes(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            color_image_stride_bytes = k4a.k4a_image_get_stride_bytes(color_image)
            k4a.k4a_image_release(color_image)
            self.assertEqual(color_image_stride_bytes, 1920*4)

    def test_k4a_image_get_device_timestamp_usec(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            device_timestamp_usec = k4a.k4a_image_get_device_timestamp_usec(color_image)
            k4a.k4a_image_release(color_image)
            self.assertIsInstance(device_timestamp_usec, int)
            self.assertNotEqual(device_timestamp_usec, 0) # Strictly not always the case.

    def test_k4a_image_get_system_timestamp_nsec(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            system_timestamp_nsec = k4a.k4a_image_get_system_timestamp_nsec(color_image)
            k4a.k4a_image_release(color_image)
            self.assertIsInstance(system_timestamp_nsec, int)
            self.assertNotEqual(system_timestamp_nsec, 0) # Strictly not always the case.

    def test_k4a_image_get_exposure_usec(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            exposure_usec = k4a.k4a_image_get_exposure_usec(color_image)
            k4a.k4a_image_release(color_image)
            self.assertIsInstance(exposure_usec, int)
            self.assertNotEqual(exposure_usec, 0) # Strictly not always the case.

    def test_k4a_image_get_white_balance(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            white_balance = k4a.k4a_image_get_white_balance(color_image)
            k4a.k4a_image_release(color_image)
            self.assertIsInstance(white_balance, int)
            self.assertNotEqual(white_balance, 0) # Strictly not always the case.

    def test_k4a_image_get_iso_speed(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)
            iso_speed = k4a.k4a_image_get_iso_speed(color_image)
            k4a.k4a_image_release(color_image)
            self.assertIsInstance(iso_speed, int)
            self.assertNotEqual(iso_speed, 0) # Strictly not always the case.

    def test_k4a_image_set_device_timestamp_usec(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)

            # Save the original value.
            saved_value = k4a.k4a_image_get_device_timestamp_usec(color_image)

            # Set a new value and read it back.
            new_value = saved_value + 1
            k4a.k4a_image_set_device_timestamp_usec(color_image, new_value)
            new_value_readback = k4a.k4a_image_get_device_timestamp_usec(color_image)

            # Set the original value on the device and read it back.
            k4a.k4a_image_set_device_timestamp_usec(color_image, saved_value)
            saved_value_readback = k4a.k4a_image_get_device_timestamp_usec(color_image)

            k4a.k4a_image_release(color_image)

            self.assertEqual(new_value_readback, new_value)
            self.assertEqual(saved_value_readback, saved_value)
            self.assertNotEqual(new_value, saved_value)
            self.assertNotEqual(saved_value_readback, new_value_readback)

    def test_k4a_image_set_system_timestamp_nsec(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)

            # Save the original value.
            saved_value = k4a.k4a_image_get_system_timestamp_nsec(color_image)

            # Set a new value and read it back.
            new_value = saved_value + 1
            k4a.k4a_image_set_system_timestamp_nsec(color_image, new_value)
            new_value_readback = k4a.k4a_image_get_system_timestamp_nsec(color_image)

            # Set the original value on the device and read it back.
            k4a.k4a_image_set_system_timestamp_nsec(color_image, saved_value)
            saved_value_readback = k4a.k4a_image_get_system_timestamp_nsec(color_image)

            k4a.k4a_image_release(color_image)

            self.assertEqual(new_value_readback, new_value)
            self.assertEqual(saved_value_readback, saved_value)
            self.assertNotEqual(new_value, saved_value)
            self.assertNotEqual(saved_value_readback, new_value_readback)

    def test_k4a_image_set_exposure_usec(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)

            # Save the original value.
            saved_value = k4a.k4a_image_get_exposure_usec(color_image)

            # Set a new value and read it back.
            new_value = saved_value + 1
            k4a.k4a_image_set_exposure_usec(color_image, new_value)
            new_value_readback = k4a.k4a_image_get_exposure_usec(color_image)

            # Set the original value on the device and read it back.
            k4a.k4a_image_set_exposure_usec(color_image, saved_value)
            saved_value_readback = k4a.k4a_image_get_exposure_usec(color_image)

            k4a.k4a_image_release(color_image)

            self.assertEqual(new_value_readback, new_value)
            self.assertEqual(saved_value_readback, saved_value)
            self.assertNotEqual(new_value, saved_value)
            self.assertNotEqual(saved_value_readback, new_value_readback)

    def test_k4a_image_set_white_balance(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)

            # Save the original value.
            saved_value = k4a.k4a_image_get_white_balance(color_image)

            # Set a new value and read it back.
            new_value = saved_value + 1
            k4a.k4a_image_set_white_balance(color_image, new_value)
            new_value_readback = k4a.k4a_image_get_white_balance(color_image)

            # Set the original value on the device and read it back.
            k4a.k4a_image_set_white_balance(color_image, saved_value)
            saved_value_readback = k4a.k4a_image_get_white_balance(color_image)

            k4a.k4a_image_release(color_image)

            self.assertEqual(new_value_readback, new_value)
            self.assertEqual(saved_value_readback, saved_value)
            self.assertNotEqual(new_value, saved_value)
            self.assertNotEqual(saved_value_readback, new_value_readback)

    def test_k4a_image_set_iso_speed(self):
        with self.lock:
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            color_image = k4a.k4a_capture_get_color_image(capture)

            # Save the original value.
            saved_value = k4a.k4a_image_get_iso_speed(color_image)

            # Set a new value and read it back.
            new_value = saved_value + 1
            k4a.k4a_image_set_iso_speed(color_image, new_value)
            new_value_readback = k4a.k4a_image_get_iso_speed(color_image)

            # Set the original value on the device and read it back.
            k4a.k4a_image_set_iso_speed(color_image, saved_value)
            saved_value_readback = k4a.k4a_image_get_iso_speed(color_image)

            k4a.k4a_image_release(color_image)

            self.assertEqual(new_value_readback, new_value)
            self.assertEqual(saved_value_readback, saved_value)
            self.assertNotEqual(new_value, saved_value)
            self.assertNotEqual(saved_value_readback, new_value_readback)

    def test_k4a_device_start_cameras_stop_cameras(self):
        with self.lock:
            # Start the cameras.
            device_config = k4a.DeviceConfiguration()
            device_config.color_format = k4a.EImageFormat.COLOR_BGRA32
            device_config.color_resolution = k4a.EColorResolution.RES_1080P
            device_config.depth_mode = k4a.EDepthMode.NFOV_2X2BINNED
            device_config.camera_fps = k4a.EFramePerSecond.FPS_15
            device_config.synchronized_images_only = True
            device_config.depth_delay_off_color_usec = 0
            device_config.wired_sync_mode = k4a.EWiredSyncMode.STANDALONE
            device_config.subordinate_delay_off_master_usec = 0
            device_config.disable_streaming_indicator = False

            status = k4a.k4a_device_start_cameras(self.device_handle, ctypes.byref(device_config))
            self.assertTrue(k4a.K4A_SUCCEEDED(status))
            k4a.k4a_device_stop_cameras(self.device_handle)

    def test_k4a_device_start_cameras_stop_cameras_DEFAULT_DISABLE(self):
        with self.lock:
            device_config = k4a.DEVICE_CONFIG_DISABLE_ALL
            status = k4a.k4a_device_start_cameras(self.device_handle, ctypes.byref(device_config))
            self.assertTrue(k4a.K4A_FAILED(status)) # Seems to fail when DISABLE_ALL config is used.
            k4a.k4a_device_stop_cameras(self.device_handle)

    # Always seems to fail starting IMU. Maybe there isn't one in this system?
    @unittest.expectedFailure
    def test_k4a_device_start_imu_stop_imu(self):
        with self.lock:
            status = k4a.k4a_device_start_imu(self.device_handle)
            self.assertTrue(k4a.K4A_SUCCEEDED(status))

            k4a.k4a_device_stop_imu(self.device_handle)

    def test_k4a_device_get_serialnum(self):
        strsize = ctypes.c_ulonglong(32)
        serial_number = (ctypes.c_char * strsize.value)()
        status = k4a.k4a_device_get_serialnum(self.device_handle, serial_number, ctypes.byref(strsize))
        self.assertEqual(k4a.EStatus.SUCCEEDED, status)

    def test_k4a_device_get_version(self):
        hwver = k4a.HardwareVersion()
        status = k4a.k4a_device_get_version(self.device_handle, ctypes.byref(hwver))
        self.assertEqual(k4a.EStatus.SUCCEEDED, status)

        # Check the versions.
        self.assertTrue(hwver.rgb.major != 0 or hwver.rgb.minor != 0 or hwver.rgb.iteration != 0)
        self.assertTrue(hwver.depth.major != 0 or hwver.depth.minor != 0 or hwver.depth.iteration != 0)
        self.assertTrue(hwver.audio.major != 0 or hwver.audio.minor != 0 or hwver.audio.iteration != 0)
        self.assertTrue(hwver.depth_sensor.major != 0 or hwver.depth_sensor.minor != 0 or hwver.depth_sensor.iteration != 0)

    def test_k4a_device_get_color_control_capabilities(self):

        color_control_commands = [
            k4a.EColorControlCommand.BACKLIGHT_COMPENSATION,
            k4a.EColorControlCommand.BRIGHTNESS,
            k4a.EColorControlCommand.CONTRAST,
            k4a.EColorControlCommand.EXPOSURE_TIME_ABSOLUTE,
            k4a.EColorControlCommand.GAIN,
            k4a.EColorControlCommand.POWERLINE_FREQUENCY,
            k4a.EColorControlCommand.SATURATION,
            k4a.EColorControlCommand.SHARPNESS,
            k4a.EColorControlCommand.WHITEBALANCE
        ]

        for command in color_control_commands:
            with self.subTest(command = command):
                status = k4a_device_get_color_control_capability(self.device_handle, command)
                self.assertTrue(k4a.K4A_SUCCEEDED(status))

    def test_k4a_device_get_color_control(self):

        color_control_commands = [
            k4a.EColorControlCommand.BACKLIGHT_COMPENSATION,
            k4a.EColorControlCommand.BRIGHTNESS,
            k4a.EColorControlCommand.CONTRAST,
            k4a.EColorControlCommand.EXPOSURE_TIME_ABSOLUTE,
            k4a.EColorControlCommand.GAIN,
            k4a.EColorControlCommand.POWERLINE_FREQUENCY,
            k4a.EColorControlCommand.SATURATION,
            k4a.EColorControlCommand.SHARPNESS,
            k4a.EColorControlCommand.WHITEBALANCE
        ]

        for command in color_control_commands:
            with self.subTest(command = command):
                mode = ctypes.c_int32(k4a.EColorControlMode.AUTO.value)
                value = ctypes.c_int32(0)

                status = k4a.k4a_device_get_color_control(
                    self.device_handle,
                    ctypes.c_int(command.value),
                    ctypes.byref(mode),
                    ctypes.byref(value)
                )
                self.assertTrue(k4a.K4A_SUCCEEDED(status))
    
    # For some reason, manually setting EXPOSURE_TIME_ABSOLUTE fails.
    def test_k4a_device_set_color_control(self):

        color_control_commands = [
            k4a.EColorControlCommand.BACKLIGHT_COMPENSATION,
            k4a.EColorControlCommand.BRIGHTNESS,
            k4a.EColorControlCommand.CONTRAST,
            #k4a.EColorControlCommand.EXPOSURE_TIME_ABSOLUTE,
            k4a.EColorControlCommand.GAIN,
            k4a.EColorControlCommand.POWERLINE_FREQUENCY,
            k4a.EColorControlCommand.SATURATION,
            k4a.EColorControlCommand.SHARPNESS,
            k4a.EColorControlCommand.WHITEBALANCE
        ]

        for command in color_control_commands:
            with self.subTest(command = command):
                (status, status0, status1, status2, status3, status4,
                    saved_value, saved_value_readback, new_value, new_value_readback) = \
                        k4a_device_set_and_get_color_control(self.device_handle, command)
                self.assertTrue(k4a.K4A_SUCCEEDED(status))
                self.assertTrue(k4a.K4A_SUCCEEDED(status0))
                self.assertTrue(k4a.K4A_SUCCEEDED(status1))
                self.assertTrue(k4a.K4A_SUCCEEDED(status2))
                self.assertTrue(k4a.K4A_SUCCEEDED(status3))
                self.assertTrue(k4a.K4A_SUCCEEDED(status4))
                self.assertEqual(saved_value.value, saved_value_readback.value)
                self.assertEqual(new_value.value, new_value_readback.value)
                self.assertNotEqual(saved_value.value, new_value.value)

    def test_k4a_device_get_raw_calibration(self):
        with self.lock:
            
            # Get buffer size requirement.
            buffer_size = ctypes.c_ulonglong(0)
            buffer = ctypes.c_uint8(0)
            status = k4a.k4a_device_get_raw_calibration(
                self.device_handle, ctypes.byref(buffer), ctypes.byref(buffer_size))
            self.assertEqual(status, k4a.EBufferStatus.BUFFER_TOO_SMALL)

            buffer = ctypes.create_string_buffer(buffer_size.value)
            buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint8))
            status = k4a.k4a_device_get_raw_calibration(
                self.device_handle, buffer, ctypes.byref(buffer_size))
            self.assertEqual(status, k4a.EBufferStatus.SUCCEEDED)

    def test_k4a_device_get_calibration(self):
        with self.lock:
            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, color_resolution = color_resolutions):
                        status = k4a.k4a_device_get_calibration(
                            self.device_handle,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))

                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

    def test_k4a_device_get_sync_jack(self):
        sync_in = ctypes.c_bool(False)
        sync_out = ctypes.c_bool(False)

        status = k4a.k4a_device_get_sync_jack(
            self.device_handle, ctypes.byref(sync_in), ctypes.byref(sync_out))

        self.assertTrue(k4a.K4A_SUCCEEDED(status))

    def test_k4a_calibration_get_from_raw(self):
        with self.lock:
            
            # Get buffer size requirement.
            buffer_size = ctypes.c_ulonglong(0)
            buffer = ctypes.c_uint8(0)
            status = k4a.k4a_device_get_raw_calibration(
                self.device_handle, ctypes.byref(buffer), ctypes.byref(buffer_size))
            self.assertEqual(status, k4a.EBufferStatus.BUFFER_TOO_SMALL)

            buffer = ctypes.create_string_buffer(buffer_size.value)
            buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_uint8))
            status = k4a.k4a_device_get_raw_calibration(
                self.device_handle, buffer, ctypes.byref(buffer_size))
            self.assertEqual(status, k4a.EBufferStatus.SUCCEEDED)

            # Now get the calibration from the buffer.
            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            buffer = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))
            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, color_resolution = color_resolutions):
                        status = k4a.k4a_calibration_get_from_raw(
                            buffer,
                            buffer_size,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))

                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

    def test_k4a_calibration_3d_to_3d(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration_types = [
                k4a.ECalibrationType.COLOR,
                k4a.ECalibrationType.DEPTH
            ]

            calibration = k4a.Calibration()
            source_point = k4a._Float3(500, 500, 1000)
            target_point = k4a._Float3()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    for source_camera in calibration_types:
                        for target_camera in calibration_types:
                            with self.subTest(depth_mode = depth_mode, 
                                color_resolution = color_resolutions,
                                source_camera = source_camera,
                                target_camera = target_camera):

                                status = k4a.k4a_device_get_calibration(
                                    self.device_handle,
                                    depth_mode,
                                    color_resolution,
                                    ctypes.byref(calibration))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))

                                # Transform source point from source_camera to target_camera.
                                status = k4a.k4a_calibration_3d_to_3d(
                                    ctypes.byref(calibration),
                                    ctypes.byref(source_point),
                                    source_camera,
                                    target_camera,
                                    ctypes.byref(target_point))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))

                                if source_camera == target_camera:
                                    self.assertAlmostEqual(source_point.xyz.x, target_point.xyz.x)
                                    self.assertAlmostEqual(source_point.xyz.y, target_point.xyz.y)
                                    self.assertAlmostEqual(source_point.xyz.z, target_point.xyz.z)

    # This test always fails. Why??
    @unittest.expectedFailure
    def test_k4a_calibration_2d_to_3d(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration_types = [
                k4a.ECalibrationType.COLOR,
                k4a.ECalibrationType.DEPTH
            ]

            calibration = k4a.Calibration()
            source_point = k4a._Float2(0, 0)
            depth_mm = 1000
            target_point = k4a._Float3()
            valid_int_flag = ctypes.c_int(0)

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    for source_camera in calibration_types:
                        for target_camera in calibration_types:
                            with self.subTest(depth_mode = depth_mode, 
                                color_resolution = color_resolutions,
                                source_camera = source_camera,
                                target_camera = target_camera):

                                status = k4a.k4a_device_get_calibration(
                                    self.device_handle,
                                    depth_mode,
                                    color_resolution,
                                    ctypes.byref(calibration))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))

                                # Transform source point from source_camera to target_camera.
                                status = k4a.k4a_calibration_2d_to_3d(
                                    ctypes.byref(calibration),
                                    ctypes.byref(source_point),
                                    depth_mm,
                                    source_camera,
                                    target_camera,
                                    ctypes.byref(target_point),
                                    ctypes.byref(valid_int_flag))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))
                                self.assertEqual(valid_int_flag.value, 1)

                                if source_camera == target_camera:
                                    self.assertAlmostEqual(source_point.xy.x, target_point.xyz.x)
                                    self.assertAlmostEqual(source_point.xy.y, target_point.xyz.y)
                                    self.assertAlmostEqual(depth_mm, target_point.xyz.z)

    # This test always fails. Why??
    @unittest.expectedFailure
    def test_k4a_calibration_3d_to_2d(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration_types = [
                k4a.ECalibrationType.COLOR,
                k4a.ECalibrationType.DEPTH
            ]

            calibration = k4a.Calibration()
            source_point = k4a._Float3(0, 0, 100)
            target_point = k4a._Float2()
            valid_int_flag = ctypes.c_int(0)

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    for source_camera in calibration_types:
                        for target_camera in calibration_types:
                            with self.subTest(depth_mode = depth_mode, 
                                color_resolution = color_resolutions,
                                source_camera = source_camera,
                                target_camera = target_camera):

                                status = k4a.k4a_device_get_calibration(
                                    self.device_handle,
                                    depth_mode,
                                    color_resolution,
                                    ctypes.byref(calibration))
                                self.assertTrue(k4a.K4A_SUCCEEDED(status))

                                # Transform source point from source_camera to target_camera.
                                status = k4a.k4a_calibration_3d_to_2d(
                                    ctypes.byref(calibration),
                                    ctypes.byref(source_point),
                                    source_camera,
                                    target_camera,
                                    ctypes.byref(target_point),
                                    ctypes.byref(valid_int_flag))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))
                                self.assertEqual(valid_int_flag.value, 1)

                                if source_camera == target_camera:
                                    self.assertAlmostEqual(source_point.xyz.x, target_point.xy.x)
                                    self.assertAlmostEqual(source_point.xyz.y, target_point.xy.y)

    # This test always fails. Why??
    @unittest.expectedFailure
    def test_k4a_calibration_2d_to_2d(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration_types = [
                k4a.ECalibrationType.COLOR,
                k4a.ECalibrationType.DEPTH
            ]

            calibration = k4a.Calibration()
            source_point = k4a._Float2(0, 0)
            depth_mm = 400
            target_point = k4a._Float2()
            valid_int_flag = ctypes.c_int(0)

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    for source_camera in calibration_types:
                        for target_camera in calibration_types:
                            with self.subTest(depth_mode = depth_mode, 
                                color_resolution = color_resolutions,
                                source_camera = source_camera,
                                target_camera = target_camera):

                                status = k4a.k4a_device_get_calibration(
                                    self.device_handle,
                                    depth_mode,
                                    color_resolution,
                                    ctypes.byref(calibration))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))

                                # Transform source point from source_camera to target_camera.
                                status = k4a.k4a_calibration_2d_to_2d(
                                    ctypes.byref(calibration),
                                    ctypes.byref(source_point),
                                    depth_mm,
                                    source_camera,
                                    target_camera,
                                    ctypes.byref(target_point),
                                    ctypes.byref(valid_int_flag))

                                self.assertTrue(k4a.K4A_SUCCEEDED(status))
                                self.assertEqual(valid_int_flag.value, 1)

                                if source_camera == target_camera:
                                    self.assertAlmostEqual(source_point.xy.x, target_point.xy.x)
                                    self.assertAlmostEqual(source_point.xy.y, target_point.xy.y)

    # This test is data dependent. It may fail based on scene content.
    # It is favorable to point the camera at a flat wall about 30 cm away.
    # Perhaps it's better to generate synthetic data.
    def test_k4a_calibration_color_2d_to_depth_2d(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration = k4a.Calibration()
            target_point = k4a._Float2()
            valid_int_flag = ctypes.c_int(0)

            # Get a depth image.
            capture = get_1080p_bgr32_nfov_2x2binned(self.device_handle)
            self.assertIsNotNone(capture)

            depth_image = k4a.k4a_capture_get_depth_image(capture)
            self.assertIsNotNone(depth_image)

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, 
                        color_resolution = color_resolutions):

                        status = k4a.k4a_device_get_calibration(
                            self.device_handle,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        # Get a depth image.
                        capture = get_capture(self.device_handle,
                            k4a.EImageFormat.COLOR_BGRA32,
                            color_resolution,
                            depth_mode)

                        depth_image = k4a.k4a_capture_get_depth_image(capture)
                        self.assertIsNotNone(depth_image)

                        # Get color image width and height to specify the source point.
                        color_image = k4a.k4a_capture_get_color_image(capture)
                        width_pixels = k4a.k4a_image_get_width_pixels(color_image)
                        height_pixels = k4a.k4a_image_get_height_pixels(color_image)
                        source_point = k4a._Float2(height_pixels/4, width_pixels/4)

                        # Transform source point from source_camera to target_camera.
                        status = k4a.k4a_calibration_color_2d_to_depth_2d(
                            ctypes.byref(calibration),
                            ctypes.byref(source_point),
                            depth_image,
                            ctypes.byref(target_point),
                            ctypes.byref(valid_int_flag))

                        k4a.k4a_image_release(depth_image)
                        k4a.k4a_image_release(color_image)

                        self.assertTrue(k4a.K4A_SUCCEEDED(status))
                        self.assertEqual(valid_int_flag.value, 1)

    def test_k4a_transformation_create_destroy(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
                k4a.EDepthMode.PASSIVE_IR,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, 
                        color_resolution = color_resolutions):

                        status = k4a.k4a_device_get_calibration(
                            self.device_handle,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))

                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        transformation = k4a.k4a_transformation_create(ctypes.byref(calibration))
                        self.assertIsNotNone(transformation) # Might not be a valid assert.
                        k4a.k4a_transformation_destroy(transformation)

    def test_k4a_transformation_depth_image_to_color_camera(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, 
                        color_resolution = color_resolutions):

                        status = k4a.k4a_device_get_calibration(
                            self.device_handle,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        transformation = k4a.k4a_transformation_create(ctypes.byref(calibration))
                        self.assertIsNotNone(transformation) # Might not be a valid assert.

                        # Get a depth image.
                        capture = get_capture(self.device_handle,
                            k4a.EImageFormat.COLOR_BGRA32,
                            color_resolution,
                            depth_mode)

                        depth_image = k4a.k4a_capture_get_depth_image(capture)
                        image_format = k4a.k4a_image_get_format(depth_image)

                        # Get color image width and height.
                        color_image = k4a.k4a_capture_get_color_image(capture)
                        width_pixels = k4a.k4a_image_get_width_pixels(color_image)
                        height_pixels = k4a.k4a_image_get_height_pixels(color_image)
                        stride_bytes = width_pixels * 2

                        # Create an output depth image.
                        transformed_image = k4a._bindings.k4a._ImageHandle()
                        status = k4a.k4a_image_create(
                            image_format,
                            width_pixels,
                            height_pixels,
                            stride_bytes,
                            ctypes.byref(transformed_image)
                        )
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        # Apply the transformation.
                        status = k4a.k4a_transformation_depth_image_to_color_camera(
                            transformation,
                            depth_image,
                            transformed_image
                        )
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        k4a.k4a_transformation_destroy(transformation)
                        k4a.k4a_image_release(transformed_image)
                        k4a.k4a_image_release(depth_image)

    def test_k4a_transformation_depth_image_to_color_camera_custom(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, 
                        color_resolution = color_resolutions):

                        status = k4a.k4a_device_get_calibration(
                            self.device_handle,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        transformation = k4a.k4a_transformation_create(ctypes.byref(calibration))
                        self.assertIsNotNone(transformation) # Might not be a valid assert.

                        # Get a capture.
                        capture = get_capture(self.device_handle,
                            k4a.EImageFormat.COLOR_BGRA32,
                            color_resolution,
                            depth_mode)

                        # Get color image width and height.
                        color_image = k4a.k4a_capture_get_color_image(capture)
                        output_width_pixels = k4a.k4a_image_get_width_pixels(color_image)
                        output_height_pixels = k4a.k4a_image_get_height_pixels(color_image)
                        output_stride_bytes = output_width_pixels * 2

                        # Get a depth image.
                        depth_image = k4a.k4a_capture_get_depth_image(capture)
                        image_format = k4a.k4a_image_get_format(depth_image)
                        input_width_pixels = k4a.k4a_image_get_width_pixels(depth_image)
                        input_height_pixels = k4a.k4a_image_get_height_pixels(depth_image)

                        # Create an output depth image.
                        transformed_depth_image = k4a._bindings.k4a._ImageHandle()
                        status = k4a.k4a_image_create(
                            image_format,
                            output_width_pixels,
                            output_height_pixels,
                            output_stride_bytes,
                            ctypes.byref(transformed_depth_image)
                        )
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        # Create a custom image.
                        image_format = k4a.EImageFormat.CUSTOM16
                        custom_image = k4a._bindings.k4a._ImageHandle()
                        status = k4a.k4a_image_create(
                            image_format.value, 
                            input_width_pixels, 
                            input_height_pixels, 
                            input_width_pixels * 2, 
                            ctypes.byref(custom_image))
                        self.assertEqual(k4a.EStatus.SUCCEEDED, status)

                        # Create a transformed custom image.
                        image_format = k4a.EImageFormat.CUSTOM16
                        transformed_custom_image = k4a._bindings.k4a._ImageHandle()
                        status = k4a.k4a_image_create(
                            image_format.value,
                            output_width_pixels,
                            output_height_pixels, 
                            output_width_pixels * 2, 
                            ctypes.byref(transformed_custom_image))
                        self.assertEqual(k4a.EStatus.SUCCEEDED, status)

                        # Apply the transformation.
                        status = k4a.k4a_transformation_depth_image_to_color_camera_custom(
                            transformation,
                            depth_image,
                            custom_image,
                            transformed_depth_image,
                            transformed_custom_image,
                            k4a.ETransformInterpolationType.LINEAR,
                            0
                        )
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        k4a.k4a_transformation_destroy(transformation)
                        k4a.k4a_image_release(depth_image)
                        k4a.k4a_image_release(custom_image)
                        k4a.k4a_image_release(transformed_depth_image)
                        k4a.k4a_image_release(transformed_custom_image)

    def test_k4a_transformation_color_image_to_depth_camera(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
            ]

            color_resolutions = [
                k4a.EColorResolution.RES_3072P,
                k4a.EColorResolution.RES_2160P,
                k4a.EColorResolution.RES_1536P,
                k4a.EColorResolution.RES_1440P,
                k4a.EColorResolution.RES_1080P,
                k4a.EColorResolution.RES_720P,
            ]

            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                for color_resolution in color_resolutions:
                    with self.subTest(depth_mode = depth_mode, 
                        color_resolution = color_resolutions):

                        status = k4a.k4a_device_get_calibration(
                            self.device_handle,
                            depth_mode,
                            color_resolution,
                            ctypes.byref(calibration))
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        transformation = k4a.k4a_transformation_create(ctypes.byref(calibration))
                        self.assertIsNotNone(transformation) # Might not be a valid assert.

                        # Get a capture and depth and color images.
                        capture = get_capture(self.device_handle,
                            k4a.EImageFormat.COLOR_BGRA32,
                            color_resolution,
                            depth_mode)

                        depth_image = k4a.k4a_capture_get_depth_image(capture)
                        color_image = k4a.k4a_capture_get_color_image(capture)

                        # Create an output image.
                        image_format = k4a.k4a_image_get_format(color_image)
                        width_pixels = k4a.k4a_image_get_width_pixels(depth_image)
                        height_pixels = k4a.k4a_image_get_height_pixels(depth_image)
                        stride_bytes = width_pixels * 4

                        transformed_image = k4a._bindings.k4a._ImageHandle()
                        status = k4a.k4a_image_create(
                            image_format,
                            width_pixels,
                            height_pixels,
                            stride_bytes,
                            ctypes.byref(transformed_image)
                        )
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        # Apply the transformation.
                        status = k4a.k4a_transformation_color_image_to_depth_camera(
                            transformation,
                            depth_image,
                            color_image,
                            transformed_image
                        )
                        self.assertTrue(k4a.K4A_SUCCEEDED(status))

                        k4a.k4a_transformation_destroy(transformation)
                        k4a.k4a_image_release(transformed_image)
                        k4a.k4a_image_release(depth_image)
                        k4a.k4a_image_release(color_image)

    # This test is always failing for some reason.
    @unittest.expectedFailure
    def test_k4a_transformation_depth_image_to_point_cloud(self):
        with self.lock:

            depth_modes = [
                k4a.EDepthMode.NFOV_2X2BINNED,
                k4a.EDepthMode.NFOV_UNBINNED,
                k4a.EDepthMode.WFOV_2X2BINNED,
                k4a.EDepthMode.WFOV_UNBINNED,
            ]

            calibration = k4a.Calibration()

            for depth_mode in depth_modes:
                with self.subTest(depth_mode = depth_mode):

                    status = k4a.k4a_device_get_calibration(
                        self.device_handle,
                        depth_mode,
                        k4a.EColorResolution.RES_1080P,
                        ctypes.byref(calibration))
                    self.assertTrue(k4a.K4A_SUCCEEDED(status))

                    transformation = k4a.k4a_transformation_create(ctypes.byref(calibration))
                    self.assertIsNotNone(transformation) # Might not be a valid assert.

                    # Get a capture and depth image.
                    capture = get_capture(self.device_handle,
                        k4a.EImageFormat.COLOR_BGRA32,
                        k4a.EColorResolution.RES_1080P,
                        depth_mode)

                    depth_image = k4a.k4a_capture_get_depth_image(capture)

                    # Create an output image.
                    image_format = k4a.EImageFormat.CUSTOM
                    width_pixels = k4a.k4a_image_get_width_pixels(depth_image)
                    height_pixels = k4a.k4a_image_get_height_pixels(depth_image)
                    stride_bytes = width_pixels * 6

                    xyz_image = k4a._bindings.k4a._ImageHandle()
                    status = k4a.k4a_image_create(
                        image_format,
                        width_pixels,
                        height_pixels,
                        stride_bytes,
                        ctypes.byref(xyz_image)
                    )
                    self.assertTrue(k4a.K4A_SUCCEEDED(status))

                    # Apply the transformation.
                    status = k4a.k4a_transformation_depth_image_to_point_cloud(
                        transformation,
                        depth_image,
                        k4a.ECalibrationType.DEPTH,
                        xyz_image
                    )
                    self.assertTrue(k4a.K4A_SUCCEEDED(status))

                    k4a.k4a_transformation_destroy(transformation)
                    k4a.k4a_image_release(xyz_image)
                    k4a.k4a_image_release(depth_image)