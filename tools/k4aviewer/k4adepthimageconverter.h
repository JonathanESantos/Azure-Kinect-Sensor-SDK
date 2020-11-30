// Copyright (c) Microsoft Corporation. All rights reserved.
// Licensed under the MIT License.

#ifndef K4ADEPTHIMAGECONVERTER_H
#define K4ADEPTHIMAGECONVERTER_H

// System headers
//

// Library headers
//

// Project headers
//
#include "k4adepthimageconverterbase.h"
#include "k4adepthpixelcolorizer.h"
#include "k4astaticimageproperties.h"

namespace k4aviewer
{

class K4ADepthImageConverter
    : public K4ADepthImageConverterBase<K4A_IMAGE_FORMAT_DEPTH16, K4ADepthPixelColorizer::ColorizeBlueToRed>
{
public:
    explicit K4ADepthImageConverter(uint32_t depth_mode_id) :
        K4ADepthImageConverterBase(depth_mode_id, GetDepthModeRange(depth_mode_id))
    {
    }

    ~K4ADepthImageConverter() override = default;

    K4ADepthImageConverter(const K4ADepthImageConverter &) = delete;
    K4ADepthImageConverter(const K4ADepthImageConverter &&) = delete;
    K4ADepthImageConverter &operator=(const K4ADepthImageConverter &) = delete;
    K4ADepthImageConverter &operator=(const K4ADepthImageConverter &&) = delete;
};
} // namespace k4aviewer

#endif
