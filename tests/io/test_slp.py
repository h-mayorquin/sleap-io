"""Tests for functions in the sleap_io.io.slp file."""

from sleap_io import (
    Video,
    Skeleton,
    Edge,
    Node,
    Instance,
    LabeledFrame,
    Track,
    Point,
    PredictedPoint,
    PredictedInstance,
    Labels,
    SuggestionFrame,
)
from sleap_io.io.slp import (
    read_videos,
    write_videos,
    read_tracks,
    write_tracks,
    read_instances,
    read_metadata,
    read_skeletons,
    serialize_skeletons,
    write_metadata,
    read_points,
    read_pred_points,
    read_instances,
    write_lfs,
    read_labels,
    write_labels,
    read_suggestions,
    write_suggestions,
)
from sleap_io.io.utils import read_hdf5_dataset
import numpy as np

from sleap_io.io.video import ImageVideo


def test_read_labels(slp_typical, slp_simple_skel, slp_minimal):
    """Test `read_labels` can read different types of .slp files."""
    labels = read_labels(slp_typical)
    assert type(labels) == Labels

    labels = read_labels(slp_simple_skel)
    assert type(labels) == Labels

    labels = read_labels(slp_minimal)
    assert type(labels) == Labels


def test_load_slp_with_provenance(slp_predictions_with_provenance):
    labels = read_labels(slp_predictions_with_provenance)
    provenance = labels.provenance
    assert type(provenance) == dict
    assert provenance["sleap_version"] == "1.2.7"


def test_read_instances_from_predicted(slp_real_data):
    labels = read_labels(slp_real_data)

    lf = labels.find(video=labels.video, frame_idx=220)[0]
    assert len(lf) == 3
    assert type(lf.instances[0]) == PredictedInstance
    assert type(lf.instances[1]) == PredictedInstance
    assert type(lf.instances[2]) == Instance
    assert lf.instances[2].from_predicted == lf.instances[1]
    assert lf.unused_predictions == [lf.instances[0]]

    lf = labels.find(video=labels.video, frame_idx=770)[0]
    assert len(lf) == 4
    assert type(lf.instances[0]) == PredictedInstance
    assert type(lf.instances[1]) == PredictedInstance
    assert type(lf.instances[2]) == Instance
    assert type(lf.instances[3]) == Instance
    assert lf.instances[2].from_predicted == lf.instances[1]
    assert lf.instances[3].from_predicted == lf.instances[0]
    assert len(lf.unused_predictions) == 0


def test_read_skeleton(centered_pair):
    skeletons = read_skeletons(centered_pair)
    assert len(skeletons) == 1
    skeleton = skeletons[0]
    assert type(skeleton) == Skeleton
    assert len(skeleton.nodes) == 24
    assert len(skeleton.edges) == 23
    assert len(skeleton.symmetries) == 20
    assert Node("wingR") in skeleton.symmetries[0].nodes
    assert Node("wingL") in skeleton.symmetries[0].nodes


def test_read_videos_pkg(slp_minimal_pkg):
    videos = read_videos(slp_minimal_pkg)
    assert len(videos) == 1
    video = videos[0]
    assert video.shape == (1, 384, 384, 1)
    assert video.backend.dataset == "video0/video"


def test_write_videos(slp_minimal_pkg, centered_pair, tmp_path):
    videos = read_videos(slp_minimal_pkg)
    write_videos(tmp_path / "test_minimal_pkg.slp", videos)
    json_fixture = read_hdf5_dataset(slp_minimal_pkg, "videos_json")
    json_test = read_hdf5_dataset(tmp_path / "test_minimal_pkg.slp", "videos_json")
    assert json_fixture == json_test

    videos = read_videos(centered_pair)
    write_videos(tmp_path / "test_centered_pair.slp", videos)
    json_fixture = read_hdf5_dataset(centered_pair, "videos_json")
    json_test = read_hdf5_dataset(tmp_path / "test_centered_pair.slp", "videos_json")
    assert json_fixture == json_test

    videos = read_videos(centered_pair) * 2
    write_videos(tmp_path / "test_centered_pair_2vids.slp", videos)
    json_test = read_hdf5_dataset(
        tmp_path / "test_centered_pair_2vids.slp", "videos_json"
    )
    assert len(json_test) == 2


def test_write_tracks(centered_pair, tmp_path):
    tracks = read_tracks(centered_pair)
    write_tracks(tmp_path / "test.slp", tracks)

    # TODO: Test for byte-for-byte equality of HDF5 datasets when we implement the
    # spawned_on attribute.
    # json_fixture = read_hdf5_dataset(centered_pair, "tracks_json")
    # json_test = read_hdf5_dataset(tmp_path / "test.slp", "tracks_json")
    # assert (json_fixture == json_test).all()

    saved_tracks = read_tracks(tmp_path / "test.slp")
    assert len(saved_tracks) == len(tracks)
    for saved_track, track in zip(saved_tracks, tracks):
        assert saved_track.name == track.name


def test_write_metadata(centered_pair, tmp_path):
    labels = read_labels(centered_pair)
    write_metadata(tmp_path / "test.slp", labels)

    saved_md = read_metadata(tmp_path / "test.slp")
    assert saved_md["version"] == "2.0.0"
    assert saved_md["provenance"] == labels.provenance

    saved_skeletons = read_skeletons(tmp_path / "test.slp")
    assert len(saved_skeletons) == len(labels.skeletons)
    assert len(saved_skeletons) == 1
    assert saved_skeletons[0].name == labels.skeletons[0].name
    assert saved_skeletons[0].node_names == labels.skeletons[0].node_names
    assert saved_skeletons[0].edge_inds == labels.skeletons[0].edge_inds
    assert saved_skeletons[0].flipped_node_inds == labels.skeletons[0].flipped_node_inds


def test_write_lfs(centered_pair, slp_real_data, tmp_path):
    labels = read_labels(centered_pair)
    n_insts = len([inst for lf in labels for inst in lf])
    write_lfs(tmp_path / "test.slp", labels)

    points = read_points(tmp_path / "test.slp")
    pred_points = read_pred_points(tmp_path / "test.slp")

    assert (len(points) + len(pred_points)) == (n_insts * len(labels.skeleton))

    labels = read_labels(slp_real_data)
    n_insts = len([inst for lf in labels for inst in lf])
    write_lfs(tmp_path / "test2.slp", labels)

    points = read_points(tmp_path / "test2.slp")
    pred_points = read_pred_points(tmp_path / "test2.slp")

    assert (len(points) + len(pred_points)) == (n_insts * len(labels.skeleton))


def test_write_labels(centered_pair, slp_real_data, tmp_path):
    for fn in [centered_pair, slp_real_data]:
        labels = read_labels(fn)
        write_labels(tmp_path / "test.slp", labels)

        saved_labels = read_labels(tmp_path / "test.slp")
        assert len(saved_labels) == len(labels)
        assert [lf.frame_idx for lf in saved_labels] == [lf.frame_idx for lf in labels]
        assert [len(lf) for lf in saved_labels] == [len(lf) for lf in labels]
        np.testing.assert_array_equal(saved_labels.numpy(), labels.numpy())
        assert saved_labels.video.filename == labels.video.filename
        assert type(saved_labels.video.backend) == type(labels.video.backend)
        assert saved_labels.video.backend.grayscale == labels.video.backend.grayscale
        assert saved_labels.video.backend.shape == labels.video.backend.shape
        assert len(saved_labels.skeletons) == len(labels.skeletons) == 1
        assert saved_labels.skeleton.name == labels.skeleton.name
        assert saved_labels.skeleton.node_names == labels.skeleton.node_names
        assert len(saved_labels.suggestions) == len(labels.suggestions)


def test_load_multi_skeleton(tmpdir):
    """Test loading multiple skeletons from a single file."""
    skel1 = Skeleton()
    skel1.add_node(Node("n1"))
    skel1.add_node(Node("n2"))
    skel1.add_edge("n1", "n2")
    skel1.add_symmetry("n1", "n2")

    skel2 = Skeleton()
    skel2.add_node(Node("n3"))
    skel2.add_node(Node("n4"))
    skel2.add_edge("n3", "n4")
    skel2.add_symmetry("n3", "n4")

    skels = [skel1, skel2]
    labels = Labels(skeletons=skels)
    write_metadata(tmpdir / "test.slp", labels)

    loaded_skels = read_skeletons(tmpdir / "test.slp")
    assert len(loaded_skels) == 2
    assert loaded_skels[0].node_names == ["n1", "n2"]
    assert loaded_skels[1].node_names == ["n3", "n4"]
    assert loaded_skels[0].edge_inds == [(0, 1)]
    assert loaded_skels[1].edge_inds == [(0, 1)]
    assert loaded_skels[0].flipped_node_inds == [1, 0]
    assert loaded_skels[1].flipped_node_inds == [1, 0]


def test_slp_imgvideo(tmpdir, slp_imgvideo):
    labels = read_labels(slp_imgvideo)
    assert type(labels.video.backend) == ImageVideo
    assert labels.video.shape == (3, 384, 384, 1)

    write_labels(tmpdir / "test.slp", labels)
    labels = read_labels(tmpdir / "test.slp")
    assert type(labels.video.backend) == ImageVideo
    assert labels.video.shape == (3, 384, 384, 1)

    videos = [Video.from_filename(["fake1.jpg", "fake2.jpg"])]
    assert videos[0].shape is None
    assert len(videos[0].filename) == 2
    write_videos(tmpdir / "test2.slp", videos)
    videos = read_videos(tmpdir / "test2.slp")
    assert type(videos[0].backend) == ImageVideo
    assert len(videos[0].filename) == 2
    assert videos[0].shape is None


def test_suggestions(tmpdir):
    labels = Labels()
    labels.videos.append(Video.from_filename("fake.mp4"))
    labels.suggestions.append(SuggestionFrame(video=labels.video, frame_idx=0))

    write_suggestions(tmpdir / "test.slp", labels.suggestions, labels.videos)
    loaded_suggestions = read_suggestions(tmpdir / "test.slp", labels.videos)
    assert len(loaded_suggestions) == 1
    assert loaded_suggestions[0].video.filename == "fake.mp4"
    assert loaded_suggestions[0].frame_idx == 0

    # Handle missing suggestions dataset
    write_videos(tmpdir / "test2.slp", labels.videos)
    loaded_suggestions = read_suggestions(tmpdir / "test2.slp", labels.videos)
    assert len(loaded_suggestions) == 0
