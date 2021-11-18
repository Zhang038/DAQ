import os
from ops.argparser import argparser
from ops.os_operation import mkdir
import time
def compile_online(code_path):
    exe_path = os.path.join(code_path,"DAQscore_colab")
    if os.path.exists(exe_path):
        os.remove(exe_path)
    root_path = os.getcwd()
    os.chdir(code_path)
    os.system("make")
    os.chdir(root_path)
    if not os.path.exists(exe_path):
        print("Assign score compilation failed! Please make contact with dkihara@purdue.edu!")
    assert os.path.exists(exe_path)
    return exe_path

if __name__ == "__main__":
    params = argparser()
    if params['mode']==0:
        choose = params['gpu']
        if choose is not None:
            os.environ["CUDA_VISIBLE_DEVICES"] = choose
        cur_map_path = params['F']#os.path.abspath(params['F'])
        #process the map path if it's ending with .gz
        if ".gz"==cur_map_path[-3:]:
            from ops.os_operation import unzip_gz
            cur_map_path = unzip_gz(cur_map_path)
        model_path = os.path.abspath(params['M'])
        pdb_path = os.path.abspath(params['P'])
        save_path = os.path.join(os.getcwd(), 'Predict_Result')
        mkdir(save_path)
        #give pdb path to save computing voxels
        from data_processing.generate_trimmap import generate_trimmap
        save_path,trimmap_path = generate_trimmap(save_path,cur_map_path,pdb_path,params)
        print("Finished processing model input!")
        from predict.predict_trimmap import predict_trimmap
        output_path = os.path.join(save_path, "prediction.txt")
        #if not os.path.exists(output_path):
        output_path = predict_trimmap(trimmap_path, save_path, model_path, params)
        print("Our predictions are saved in %s, please have a check!"%output_path)
        #further call daq score to output the final score
        daq_code_path = os.path.join(os.getcwd(),"assign_score")
        exe_path = compile_online(daq_code_path)
        
        raw_score_save_path = os.path.join(save_path,"dqa_raw_score.pdb")
        os.system("chmod 777 "+exe_path)
        map_name = os.path.split(cur_map_path)[1].replace(".mrc", "")
        new_map_path = os.path.join(save_path,map_name+"_new.mrc")
        os.system(exe_path+" -i "+new_map_path+" -p "+output_path+" -Q "+str(pdb_path)+" >"+raw_score_save_path)

        #smooth the score to give the final output
        from ops.process_raw_score import read_pdb_info,get_resscore,save_pdb_with_score,read_chain_set
        window_size = params['window']
        score_save_path = os.path.join(save_path,"dqa_score_w"+str(window_size)+".pdb")
        chain_list = read_chain_set(pdb_path)
        print("total different chains:",chain_list)
        for chain_name in chain_list:
            score_chain_save_path = os.path.join(save_path,"dqa_score_w"+str(window_size)+"_"+str(chain_name)+".pdb")
            score_dict = get_resscore(raw_score_save_path,window_size,chain_name)
            residue_dict = read_pdb_info(pdb_path,chain_name)
            save_pdb_with_score(score_dict, residue_dict,score_chain_save_path)
        #concat all chain visualization together
        with open(score_save_path,'w') as wfile:
            for chain_name in chain_list:
                score_chain_save_path = os.path.join(save_path,"dqa_score_w"+str(window_size)+"_"+str(chain_name)+".pdb")
                with open(score_chain_save_path,'r') as rfile:
                    line = rfile.readline()
                    while line:
                        wfile.write(line)
                        line = rfile.readline()
        print("Please check result here: %s"%score_save_path)
        print("Please open it in pymol and visualize it by putting the following command to Pymol:")
        print("-"*100)
        print("spectrum b, blue_white_red,  all, -1,1")
        print("-"*100)