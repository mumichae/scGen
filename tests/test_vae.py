import os

import anndata
import numpy as np
import scanpy as sc

import scgen

if not os.getcwd().endswith("tests"):
    os.chdir("./tests")


def test_train_whole_data_one_celltype_out(data_name="pbmc",
                                           z_dim=50,
                                           alpha=0.1,
                                           n_epochs=1000,
                                           batch_size=32,
                                           dropout_rate=0.25,
                                           learning_rate=0.001,
                                           condition_key="condition"):
    if data_name == "pbmc":
        cell_type_to_monitor = "CD4T"
        stim_key = "stimulated"
        ctrl_key = "control"
        cell_type_key = "cell_type"
        train = sc.read("../data/train.h5ad")
    elif data_name == "hpoly":
        cell_type_to_monitor = None
        stim_key = "Hpoly.Day10"
        ctrl_key = "Control"
        cell_type_key = "cell_label"
        train = sc.read("../data/ch10_train_7000.h5ad")
    elif data_name == "salmonella":
        cell_type_to_monitor = None
        stim_key = "Salmonella"
        ctrl_key = "Control"
        cell_type_key = "cell_label"
        train = sc.read("../data/chsal_train_7000.h5ad")
    elif data_name == "species":
        cell_type_to_monitor = "rat"
        stim_key = "LPS6"
        ctrl_key = "unst"
        cell_type_key = "species"
        train = sc.read("../data/train_all_lps6.h5ad")

    for cell_type in train.obs[cell_type_key].unique().tolist():
        if cell_type_to_monitor is not None and cell_type_to_monitor != cell_type:
            continue
        os.makedirs(f"./vae_results/{data_name}/{cell_type}/", exist_ok=True)
        os.chdir(f"./vae_results/{data_name}/{cell_type}")
        net_train_data = train[~((train.obs[cell_type_key] == cell_type) & (train.obs[condition_key] == stim_key))]
        network = scgen.VAEArith(x_dimension=net_train_data.X.shape[1],
                                 z_dimension=z_dim,
                                 alpha=alpha,
                                 dropout_rate=dropout_rate,
                                 learning_rate=learning_rate,
                                 model_path=f"./")

        # network.restore_model()
        network.train(net_train_data, n_epochs=n_epochs, batch_size=batch_size, verbose=2)
        print(f"network_{cell_type} has been trained!")

        latent = network.to_latent(net_train_data.X)
        latent = sc.AnnData(X=latent,
                            obs={condition_key: net_train_data.obs[condition_key].tolist(),
                                 cell_type_key: net_train_data.obs[cell_type_key].tolist()})
        sc.pp.neighbors(latent)
        sc.tl.umap(latent)
        sc.pl.umap(latent, color=[condition_key, cell_type_key],
                   save=f"_latent_{z_dim}",
                   show=False)

        cell_type_data = train[train.obs[cell_type_key] == cell_type]

        pred, delta = network.predict(adata=cell_type_data, conditions={"ctrl": ctrl_key, "stim": stim_key},
                                      celltype_to_predict=cell_type)

        pred_adata = anndata.AnnData(pred, obs={condition_key: ["pred"] * len(pred)},
                                     var={"var_names": cell_type_data.var_names})
        all_adata = cell_type_data.concatenate(pred_adata)
        sc.tl.rank_genes_groups(cell_type_data, groupby=condition_key, n_genes=100)
        diff_genes = cell_type_data.uns["rank_genes_groups"]["names"][stim_key]

        scgen.plotting.reg_mean_plot(all_adata, condition_key=condition_key,
                                     axis_keys={"x": stim_key, "y": "pred"},
                                     gene_list=diff_genes[:5],
                                     path_to_save=f"./figures/reg_mean_all_genes.pdf")

        scgen.plotting.reg_var_plot(all_adata, condition_key=condition_key,
                                    axis_keys={"x": stim_key, "y": "pred"},
                                    gene_list=diff_genes[:5],
                                    path_to_save=f"./figures/reg_var_all_genes.pdf")

        all_adata_top_100_genes = all_adata.copy()[:, diff_genes.tolist()]

        scgen.plotting.reg_mean_plot(all_adata_top_100_genes, condition_key=condition_key,
                                     axis_keys={"x": stim_key, "y": "pred"},
                                     gene_list=diff_genes[:5],
                                     path_to_save=f"./figures/reg_mean_top_100_genes.pdf")

        scgen.plotting.reg_var_plot(all_adata_top_100_genes, condition_key=condition_key,
                                    axis_keys={"x": stim_key, "y": "pred"},
                                    gene_list=diff_genes[:5],
                                    path_to_save=f"./figures/reg_var_top_100_genes.pdf")

        all_adata_top_50_genes = all_adata.copy()[:, diff_genes.tolist()[:50]]

        scgen.plotting.reg_mean_plot(all_adata_top_50_genes, condition_key=condition_key,
                                     axis_keys={"x": stim_key, "y": "pred"},
                                     gene_list=diff_genes[:5],
                                     path_to_save=f"./figures/reg_mean_top_50_genes.pdf")

        scgen.plotting.reg_var_plot(all_adata_top_50_genes, condition_key=condition_key,
                                    axis_keys={"x": stim_key, "y": "pred"},
                                    gene_list=diff_genes[:5],
                                    path_to_save=f"./figures/reg_var_top_50_genes.pdf")

        sc.pp.neighbors(all_adata)
        sc.tl.umap(all_adata)
        sc.pl.umap(all_adata, color=condition_key,
                   save="pred_all_genes")

        sc.pp.neighbors(all_adata_top_100_genes)
        sc.tl.umap(all_adata_top_100_genes)
        sc.pl.umap(all_adata_top_100_genes, color=condition_key,
                   save="pred_top_100_genes")

        sc.pp.neighbors(all_adata_top_50_genes)
        sc.tl.umap(all_adata_top_50_genes)
        sc.pl.umap(all_adata_top_50_genes, color=condition_key,
                   save="pred_top_50_genes")

        sc.pl.violin(all_adata, keys=diff_genes.tolist()[0], groupby=condition_key,
                     save=f"_{diff_genes.tolist()[0]}")

        os.chdir("../../../")


def reconstruct_whole_data(data_name="pbmc", condition_key="condition"):
    if data_name == "pbmc":
        stim_key = "stimulated"
        ctrl_key = "control"
        cell_type_key = "cell_type"
        train = sc.read("../data/train.h5ad")
    elif data_name == "hpoly":
        stim_key = "Hpoly.Day10"
        ctrl_key = "Control"
        cell_type_key = "cell_label"
        train = sc.read("../data/ch10_train_7000.h5ad")
    elif data_name == "salmonella":
        stim_key = "Salmonella"
        ctrl_key = "Control"
        cell_type_key = "cell_label"
        train = sc.read("../data/chsal_train_7000.h5ad")
    elif data_name == "species":
        stim_key = "LPS6"
        ctrl_key = "unst"
        cell_type_key = "species"
        train = sc.read("../data/train_all_lps6.h5ad")
    all_data = anndata.AnnData()
    for idx, cell_type in enumerate(train.obs[cell_type_key].unique().tolist()):
        print(f"Reconstructing for {cell_type}")
        os.chdir(f"./results/{data_name}/{cell_type}")
        net_train_data = train[~((train.obs[cell_type_key] == cell_type) & (train.obs[condition_key] == stim_key))]
        network = scgen.MMDCVAE(x_dimension=net_train_data.X.shape[1], z_dimension=50, alpha=0.001, beta=100,
                                batch_mmd=True, kernel="multi-scale-rbf", train_with_fake_labels=False,
                                model_path=f"./")
        network.restore_model()

        cell_type_data = train[train.obs[cell_type_key] == cell_type]
        cell_type_ctrl_data = train[((train.obs[cell_type_key] == cell_type) & (train.obs[condition_key] == ctrl_key))]
        unperturbed_data = train[((train.obs[cell_type_key] == cell_type) & (train.obs[condition_key] == ctrl_key))]
        true_labels = np.zeros((len(unperturbed_data), 1))
        fake_labels = np.ones((len(unperturbed_data), 1))
        pred = network.predict(data=unperturbed_data, encoder_labels=true_labels, decoder_labels=fake_labels)
        ctrl_reconstructed = network.predict(data=cell_type_ctrl_data,
                                             encoder_labels=np.zeros(shape=(len(cell_type_ctrl_data), 1)),
                                             decoder_labels=np.zeros(shape=(len(cell_type_ctrl_data), 1)))
        pred_adata = anndata.AnnData(pred, obs={condition_key: [f"{cell_type}_pred_stim"] * len(pred)},
                                     var={"var_names": cell_type_data.var_names})
        ctrl_adata = anndata.AnnData(ctrl_reconstructed,
                                     obs={condition_key: [f"{cell_type}_ctrl"] * len(ctrl_reconstructed)},
                                     var={"var_names": cell_type_data.var_names})
        if data_name == "pbmc":
            real_stim = cell_type_data[cell_type_data.obs[condition_key] == stim_key].X.A
        else:
            real_stim = cell_type_data[cell_type_data.obs[condition_key] == stim_key].X
        real_stim_adata = anndata.AnnData(real_stim,
                                          obs={condition_key: [f"{cell_type}_real_stim"] * len(real_stim)},
                                          var={"var_names": cell_type_data.var_names})
        if idx == 0:
            all_data = ctrl_adata.concatenate(pred_adata, real_stim_adata)
        else:
            all_data = all_data.concatenate(ctrl_adata, pred_adata, real_stim_adata)

        os.chdir("../../../")
        print(f"Finish Reconstructing for {cell_type}")
    all_data.write_h5ad(f"./results/{data_name}/reconstructed.h5ad")


if __name__ == '__main__':
    test_train_whole_data_one_celltype_out(data_name="pbmc",
                                           z_dim=100,
                                           alpha=0.00001,
                                           n_epochs=300,
                                           batch_size=128,
                                           dropout_rate=0.25,
                                           learning_rate=0.001,
                                           condition_key="condition")
    # test_train_whole_data_one_celltype_out(data_name="hpoly",
    #                                        z_dim=100,
    #                                        alpha=0.001,
    #                                        n_epochs=250,
    #                                        batch_size=64,
    #                                        condition_key="condition")
    # test_train_whole_data_one_celltype_out(data_name="salmonella",
    #                                        z_dim=100,
    #                                        alpha=0.001,
    #                                        n_epochs=250,
    #                                        batch_size=64,
    #                                        condition_key="condition")
    # reconstruct_whole_data(data_name="species")
    # reconstruct_whole_data(data_name="salmonella")
