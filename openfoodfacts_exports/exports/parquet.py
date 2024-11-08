import logging
import tempfile
from pathlib import Path

import duckdb
from huggingface_hub import HfApi

logger = logging.getLogger(__name__)


SQL_QUERY = r"""
SET threads to 4;
SET preserve_insertion_order = false;
COPY ( 
    SELECT
        code,
        additives_n,
        additives_tags,
        allergens_from_ingredients,
        allergens_from_user,
        allergens_tags,
        brands_tags,
        categories_properties_tags,
        categories,
        checkers_tags,
        cities_tags,
        compared_to_category,
        complete,
        completeness,
        correctors_tags,
        countries_tags,
        created_t,
        creator,
        data_quality_errors_tags,
        data_quality_info_tags,
        data_quality_warnings_tags,
        data_sources_tags,
        ecoscore_data,
        ecoscore_grade,
        ecoscore_score,
        ecoscore_tags,
        editors,
        emb_codes,
        emb_codes_tags,
        entry_dates_tags,
        environment_impact_level,
        food_groups_tags,
        forest_footprint_data,
        generic_name,
        grades,
        images,
        informers_tags,
        ingredients_analysis_tags,
        ingredients_from_palm_oil_n,
        ingredients_n,
        ingredients_tags,
        ingredients_text_with_allergens,
        ingredients_text,
        COLUMNS('ingredients_text_\w{2}$'),
        ingredients_with_specified_percent_n,
        ingredients_with_unspecified_percent_n,
        ciqual_food_name_tags,
        ingredients_percent_analysis,
        ingredients_original_tags,
        ingredients_without_ciqual_codes_n,
        ingredients_without_ciqual_codes,
        ingredients,
        known_ingredients_n,
        labels_tags,
        lang,
        languages_tags,
        languages_codes,
        last_edit_dates_tags,
        last_editor,
        last_image_t,
        last_modified_by,
        last_modified_t,
        last_updated_t,
        link,
        main_countries_tags,
        manufacturing_places,
        manufacturing_places_tags,
        max_imgid,
        misc_tags,
        minerals_tags,
        new_additives_n,
        no_nutrition_data,
        nova_group,
        nova_groups,
        nova_groups_markers,
        nova_groups_tags,
        nucleotides_tags,
        nutrient_levels_tags,
        unknown_nutrients_tags,
        nutriments,
        nutriscore_data,
        nutriscore_grade,
        nutriscore_score,
        nutriscore_tags,
        nutrition_data_prepared_per,
        nutrition_data,
        nutrition_grades_tags,
        nutrition_score_beverage,
        nutrition_score_warning_fruits_vegetables_nuts_estimate_from_ingredients,
        nutrition_score_warning_no_fiber,
        nutrition_score_warning_no_fruits_vegetables_nuts,
        obsolete_since_date,
        obsolete,
        origins_tags,
        packaging_recycling_tags,
        packaging_shapes_tags,
        packaging_tags,
        packagings_materials,
        packagings_n,
        packagings_n,
        photographers,
        pnns_groups_1_tags,
        pnns_groups_2_tags,
        popularity_key,
        popularity_tags,
        product_name,
        product_quantity_unit,
        product_quantity,
        purchase_places_tags,
        quantity,
        rev,
        scans_n,
        scores,
        serving_quantity,
        serving_size,
        sources,
        sources_fields,
        specific_ingredients,
        states_tags,
        stores,
        stores_tags,
        traces_tags,
        unique_scans_n,
        unknown_ingredients_n,
        vitamins_tags,
        weighers_tags,
        with_non_nutritive_sweeteners,
        with_sweeteners,
    FROM read_ndjson('{dataset_path}', ignore_errors=True)
) TO '{output_path}' (FORMAT PARQUET)
;
"""


def export_parquet(dataset_path: Path) -> None:
    """Convert a JSONL dataset to Parquet format and push it to Hugging Face
    Hub."""
    logger.info("Starting conversion of JSONL to Parquet (to HF)")
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = Path(tmp_dir) / "converted_data.parquet"
        convert_jsonl_to_parquet(output_file_path=file_path, dataset_path=dataset_path)
        push_parquet_file_to_hf(data_path=file_path)


def convert_jsonl_to_parquet(
    output_file_path: Path,
    dataset_path: Path,
) -> None:
    logger.info("Start JSONL to Parquet conversion process.")
    if not dataset_path.exists():
        raise FileNotFoundError(f"{str(dataset_path)} was not found.")
    query = SQL_QUERY.replace("{dataset_path}", str(dataset_path)).replace(
        "{output_path}", str(output_file_path)
    )
    try:
        duckdb.sql(query)
    except duckdb.Error as e:
        logger.error(f"Error executing query: {query}\nError message: {e}")
        raise
    logger.info("JSONL successfully converted into Parquet file.")


def push_parquet_file_to_hf(
    data_path: Path,
    repo_id: str = "openfoodfacts/product-database",
    revision: str = "main",
    commit_message: str = "Database updated",
) -> None:
    logger.info(f"Start pushing data to Hugging Face at {repo_id}")
    if not data_path.exists():
        raise FileNotFoundError(f"Data is missing: {data_path}")
    if data_path.suffix != ".parquet":
        raise ValueError(f"A parquet file is expected. Got {data_path.suffix} instead.")
    # We use the HF_Hub api since it gives us way more flexibility than
    # push_to_hub()
    HfApi().upload_file(
        path_or_fileobj=data_path,
        repo_id=repo_id,
        revision=revision,
        repo_type="dataset",
        path_in_repo="products.parquet",
        commit_message=commit_message,
    )
    logger.info(f"Data succesfully pushed to Hugging Face at {repo_id}")
