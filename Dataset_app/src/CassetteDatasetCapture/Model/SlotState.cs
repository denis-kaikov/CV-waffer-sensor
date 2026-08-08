namespace CassetteDatasetCapture.Model;

public enum SlotState
{
    Empty = 0,
    OccupiedOk = 1,
    CrossSlot = 2,
    ShiftedInSlot = 3,
    DoubleLoadedSuspect = 4,
    Uncertain = 5
}
