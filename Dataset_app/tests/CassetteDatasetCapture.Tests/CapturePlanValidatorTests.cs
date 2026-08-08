using CassetteDatasetCapture.CapturePlan;
using CapturePlanModel = CassetteDatasetCapture.CapturePlan.CapturePlan;

namespace CassetteDatasetCapture.Tests;

public class CapturePlanValidatorTests
{
    [Fact]
    public void ValidPlanHasNoErrors()
    {
        var plan = new CapturePlanModel
        {
            SlotCount = 3,
            Configs = [new CaptureConfig { Id = "cfg_1", NormalOccupancy = "100", BlockedSlots = "100", SlotStates = "100" }]
        };

        Assert.Empty(CapturePlanValidator.Validate(plan));
    }
}
