from mf_lab.training.coco_paths import (
    canonical_coco_filename,
    coco_http_url,
    coco_zip_member,
)


def test_compact_aigenbench_coco_id_is_canonicalized():
    assert canonical_coco_filename("COCO2017_train/468706") == "000000468706.jpg"
    assert (
        coco_http_url("COCO2017_train/468706")
        == "https://images.cocodataset.org/train2017/000000468706.jpg"
    )
    assert coco_zip_member("COCO2017_train/468706") == "train2017/000000468706.jpg"


def test_already_canonical_coco_filename_stays_canonical():
    assert canonical_coco_filename("COCO2017_val/000000564127.jpg") == "000000564127.jpg"
    assert (
        coco_http_url("COCO2017_val/000000564127.jpg")
        == "https://images.cocodataset.org/val2017/000000564127.jpg"
    )
    assert coco_zip_member("COCO2017_val/000000564127.jpg") == "val2017/000000564127.jpg"
